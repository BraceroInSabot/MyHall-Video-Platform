import urllib
import requests

from decouple import config

from django.shortcuts import render, redirect

from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
# from django.forms import formset_factory
from django.http import Http404, JsonResponse
from django.forms.utils import ErrorList
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from core.forms import *
from core.models import Hall

YOUTUBE_API_KEY = config("YT_API_KEY", cast=str)

def home(request):
    explore = Hall.objects.order_by("?")[:5]
    most_recent = Hall.objects.all().order_by('-id')[:5]
    return render(request, 'index/index.html', {"random_halls":explore, "most_recent":most_recent})


def explore(request):
    explore = Hall.objects.order_by("?").all()

    return render(request, "index/explore.html", {"explore":explore})


def recent(request):
    most_recent = Hall.objects.all().order_by('-id')

    return render(request, "index/recent.html", {"recent":most_recent})


@login_required
def dashboard(request):
    halls = Hall.objects.filter(user=request.user)
    return render(request, 'dashboard/dashboard.html', {"halls":halls})

@login_required
def add_video(request, pk):
    # Repetição de formulários:
    # VideoFormSet = formset_factory(VideoForm, extra=5)

    form = VideoForm()
    search_form = SearchForm()
    hall = Hall.objects.get(pk=pk)

    # if is not the user of the original post, gets error
    if not hall.user == request.user:
            raise Http404

    if request.method == "POST":
        form = VideoForm(request.POST)     

        # Form validation
        if form.is_valid():
            video = Video()
            video.hall = hall

            video.url = form.cleaned_data['url']
            
            parsed_url = urllib.parse.urlparse(video.url)
            video_id = urllib.parse.parse_qs(parsed_url.query).get("v")

            # Consuming the Youtube API. visit http://console.developers.google.com/
            
            if video_id:

                video.youtube_id = video_id[0]
                response = requests.get(f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={video_id[0]}&key={YOUTUBE_API_KEY}")
                video_data = response.json()
                # print(f"\n\n\n\n\n\n\n\n\n\n{video_data}\n\n\n\n\n\n\n\n\n\n")
                title = video_data['items'][0]["snippet"]["title"]

                video.title = title       
                
                video.save()
                return redirect("detail_hall", pk)

                # Error handling
            else:
                errors = form._errors.setdefault("url", ErrorList())
                errors.append("Needs to be a Youtube URL")


    return render(request, "video/add_video.html", {"form":form, "search_form":search_form, "hall": hall})

@login_required
def video_search(request):
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        encoded_search_term = urllib.parse.quote(search_form.cleaned_data["search_term"])
        response = requests.get(f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&q={encoded_search_term}&key={YOUTUBE_API_KEY}")
        
        return JsonResponse(response.json())
    return JsonResponse({"Hello": "Not able to validate form"})


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("home")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        """
        User Stay logged in after SignUp in the site
        """
        validation = super(SignUpView, self).form_valid(form) # 5. Super herda de SignUpView a presente função com o parametro do usuario autenticado
        username, password = form.cleaned_data.get("username"), form.cleaned_data.get("password1") # 1. Pega os dados dos inputs
        user = authenticate(username=username, password=password) # 2. Autentica o Usuário
        login(self.request, user) # 3. Loga com o usuário autenticado
        return validation # 4. retorna a variavel (ativa ela)


class CreateHall(LoginRequiredMixin, generic.CreateView):
    model = Hall
    fields = ["title"]
    template_name = "halls/create_hall.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        form.instance.user = self.request.user
        super(CreateHall, self).form_valid(form)
        return redirect("dashboard")


class DetailHall(generic.DetailView):
    model = Hall
    template_name = "halls/detail_hall.html"


class UpdateHall(LoginRequiredMixin, generic.UpdateView):
    model = Hall
    template_name = "halls/update_hall.html"
    fields = ["title"]
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        hall = super(UpdateHall, self).get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall

class DeleteHall(LoginRequiredMixin, generic.DeleteView):
    model = Hall
    template_name = "halls/delete_hall.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        hall = super(DeleteHall, self).get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall


class DeleteVideo(LoginRequiredMixin, generic.DeleteView):
    model = Video
    template_name = "video/delete_video.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        video = super(DeleteHall, self).get_object()
        if not video.hall.user == self.request.user:
            raise Http404
        return video


def error_500(request):
    data = {}
    return render(request, "error/500.html", data)