from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("item/<int:pk>/", views.movie_detail, name="movie-detail"),
    path("detail/<str:imdb_id>/", views.movie_detail_imdb, name="movie-detail-imdb"),
    path("api/detail/<str:imdb_id>/", views.movie_api_json, name="movie-api-json"),
]
