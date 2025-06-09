from rest_framework.views import APIView
from rest_framework.response import Response
import redis
import hashlib
import requests
import os
from django.conf import settings
from tasks.tasks import sync_replica, send_email_notification
from .serializers import KeyValueSerializer

class KeyValueView(APIView):
    nodes = {
        'node1': 'http://node1:8000',
        'node2': 'http://node2:8000',
        'node3': 'http://node3:8000'
    }
    def choose_replica(self, primary):
        ids = list(self.nodes.keys())
        start = (ids.index(primary) + 1) % len(ids)
        for step in range(1, len(ids)+1):
            cand = ids[(start + step - 1) % len(ids)]
            status = self.get_redis().get(f"node_status:{cand}")
            if not status or status.decode() == "up":
                return cand
        return None          # không còn node nào sống


    def get_redis(self):
        redis_host = os.getenv('REDIS_HOST', settings.REDIS_HOST)
        return redis.Redis(host=redis_host, port=settings.REDIS_PORT)

    def get_node_for_key(self, key):
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        node_index = hash_value % len(self.nodes)
        node_id = list(self.nodes.keys())[node_index]
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        status = redis_client.get(f"node_status:{node_id}")
        if status and status.decode() == "down":
            node_index = (node_index + 1) % len(self.nodes)
            node_id = list(self.nodes.keys())[node_index]
        return node_id

    def get(self, request):  # GET
        key = request.query_params.get('key')
        target_node = self.get_node_for_key(key)
        if target_node == os.getenv('NODE_ID'):
            value = self.get_redis().get(key)
            return Response({"key": key, "value": value.decode() if value else None})
        else:
            response = requests.get(f"{self.nodes[target_node]}/kv/", params={"key": key})
            return Response(response.json())

    # POST (PUT)
    def post(self, request):
        serializer = KeyValueSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        key   = serializer.validated_data['key']
        value = serializer.validated_data['value']
        is_replica = request.query_params.get("replica") == "true"

        # 🔒 1. Nếu là gói replica, LUÔN ghi local - KHÔNG forward
        if is_replica:
            self.get_redis().set(key, value)
            return Response({"key": key, "value": value, "replica": True})

        # 🔒 2. Request gốc: xác định node chính rồi xử lý như cũ
        target_node = self.get_node_for_key(key)

        if target_node == os.getenv("NODE_ID"):
            # ghi local
            self.get_redis().set(key, value)

            # sync sang replica
            replica_node = self.choose_replica(target_node)
            if replica_node:
                sync_replica(key, value, self.nodes[replica_node])
                send_email_notification(key, value)
            return Response({"key": key, "value": value})


        # forward tới node chính (request gốc, KHÔNG gắn replica)
        resp = requests.post(f"{self.nodes[target_node]}/kv/", json=serializer.validated_data, timeout=3)
        return Response(resp.json(), status=resp.status_code)


    # DELETE
    def delete(self, request):
        key = request.query_params.get("key")
        is_replica = request.query_params.get("replica") == "true"

        if is_replica:
            self.get_redis().delete(key)
            return Response({"status": "deleted", "replica": True})

        target_node = self.get_node_for_key(key)

        if target_node == os.getenv("NODE_ID"):
            self.get_redis().delete(key)
            replica_node = self.choose_replica(target_node)
            if replica_node:
                sync_replica(key, None, self.nodes[replica_node])
                send_email_notification(key, "Deleted")
            return Response({"status": "Deleted"})

        if target_node == os.getenv("NODE_ID"):

                return Response({"status": "deleted"})

        resp = requests.delete(f"{self.nodes[target_node]}/kv/",
                            params={"key": key}, timeout=3)
        return Response(resp.json(), status=resp.status_code)

class HealthView(APIView):
    def get(self, request):
        return Response({"status": "healthy"})

class SnapshotView(APIView):
    def get_redis(self):
        redis_host = os.getenv('REDIS_HOST', settings.REDIS_HOST)
        return redis.Redis(host=redis_host, port=settings.REDIS_PORT)

    def get(self, request):
        redis_client = self.get_redis()
        keys = redis_client.keys('*')
        data = {}
        for key in keys:
            key_str = key.decode()
            key_type = redis_client.type(key_str).decode()
            if key_type == 'string':
                value = redis_client.get(key)
                data[key_str] = value.decode() if value else None
            else:
                data[key_str] = f"<non-string type: {key_type}>"
        return Response(data)  # ✅ MUST RETURN THIS

class RestoreView(APIView):
    """
    Gọi:  POST /restore/?from=node2
    Body: {}
    Node hiện tại sẽ GET /snapshot/ từ node2 và nạp lại Redis
    """
    nodes = {
        'node1': 'http://node1:8000',
        'node2': 'http://node2:8000',
        'node3': 'http://node3:8000'
    }

    def get_redis(self):
        redis_host = os.getenv('REDIS_HOST', settings.REDIS_HOST)
        return redis.Redis(host=redis_host, port=settings.REDIS_PORT)

    def post(self, request):
        src = request.query_params.get("from")      # vd: node2
        if src not in self.nodes:
            return Response({"error": "invalid node"}, status=400)

        try:
            snap = requests.get(f"{self.nodes[src]}/snapshot/", timeout=5).json()
        except Exception as e:
            return Response({"error": str(e)}, status=502)

        r = self.get_redis()
        for k, v in snap.items():
            if not v.startswith("<non-string"):
                r.set(k, v)

        return Response({"restored": len(snap)})
