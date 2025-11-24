# project/urls.py
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from accounts.views import home, service_worker, offline



urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("", home, name="root"),
    path("", include(("gifter.urls", "gifter"), namespace="gifter")),
    path("offline/", offline, name="offline"),
    path("service-worker.js", service_worker, name="service-worker"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
