from django.urls import path
from .views import KeyValueView, HealthView, SnapshotView, RestoreView

urlpatterns = [
    path('kv/', KeyValueView.as_view(), name='key-value'),
    path('health/', HealthView.as_view(), name='health'),
    path('snapshot/', SnapshotView.as_view(), name='snapshot'),
    path("restore/", RestoreView.as_view()),

]
