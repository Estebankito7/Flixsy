from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("item/<int:pk>/<str:media_type>/", views.movie_detail, name="movie-detail-typed"),
    path("item/<int:pk>/", views.movie_detail, name="movie-detail"),
    path("detail/<str:imdb_id>/", views.movie_detail_imdb, name="movie-detail-imdb"),
    path("api/detail/<str:imdb_id>/", views.movie_api_json, name="movie-api-json"),
    path("api/trending/", views.trending_api, name="trending-api"),
    path("search/", views.search_results, name="search"),
    path("search/api/", views.search_api, name="search-api"),
    path("saved/", views.saved_list, name="saved"),
]
