from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, AuthViewSet, SlideshowPublicListView,  SlideshowImageListCreateView,  SlideshowImageDetailView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'auth', AuthViewSet, basename='auth')


urlpatterns = [
    path('', include(router.urls)),
    
   
]

slideshow_urlpatterns = [
    # Public — no auth, called by login page
    path('slideshow/public/', SlideshowPublicListView.as_view(),        name='slideshow-public'),
 
    # Admin — auth required
    path('slideshow/',         SlideshowImageListCreateView.as_view(),  name='slideshow-list-create'),
    path('slideshow/<uuid:pk>/', SlideshowImageDetailView.as_view(),     name='slideshow-detail'),
]
 

