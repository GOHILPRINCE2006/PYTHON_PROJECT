# recommendox/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg, F
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django import forms
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegistrationForm, ContentForm, ReviewForm 
from .models import (
    Content, UserProfile, GoldenUser, Watchlist, 
    Rating, Review, Analytics, Message, Reviewer, ContentOTT, ContentCreator
)

#HELPER FUNCTIONS 
def is_reviewer(user):
    """Check if user has reviewer role"""
    if not user.is_authenticated:
        return False
    try:
        return hasattr(user.profile, 'reviewer_profile') and user.profile.reviewer_profile.is_active
    except:
        return False

def is_content_creator(user):
    """Check if user has content creator role"""
    if not user.is_authenticated:
        return False
    try:
        return hasattr(user.profile, 'creator_profile') and user.profile.creator_profile.is_active
    except:
        return False

def content_creator_required(view_func):
    """Decorator to check if user is content creator"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('recommendox:login')
        
        if request.user.is_staff:  
            return view_func(request, *args, **kwargs)
        
        if is_content_creator(request.user):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'You need to be a verified content creator to access this page.')
        return redirect('recommendox:user_dashboard')
    return wrapper

def get_personalized_recommendations(user):
    """Generate personalized recommendations based on user activity"""
    recommendations = []
    seen_ids = set()  
   
    user_ratings = Rating.objects.filter(user=user)
    if user_ratings.exists():
        from collections import Counter
        genre_counter = Counter()
        
        for rating in user_ratings:
            if rating.rating_value >= 4: 
                genre_counter[rating.content.genre] += rating.rating_value
        
        if genre_counter:
            top_genres = [genre for genre, count in genre_counter.most_common(2)]
           
            for genre in top_genres:
                genre_content = Content.objects.filter(
                    genre=genre
                ).exclude(
                    id__in=user_ratings.values_list('content_id', flat=True)
                ).order_by('-ratings__rating_value')[:3]
                
                for content in genre_content:
                    if content.id not in seen_ids: 
                        recommendations.append(content)
                        seen_ids.add(content.id)
   
    if len(recommendations) < 6:
        additional = Content.objects.exclude(
            id__in=seen_ids 
        ).order_by('-ratings__rating_value')[:6-len(recommendations)]
        
        for content in additional:
            if content.id not in seen_ids:
                recommendations.append(content)
                seen_ids.add(content.id)
    
    return recommendations[:6] 

#PUBLIC VIEWS
def home(request):
    """Public home page"""
    from django.db.models import Avg, Count
    from datetime import datetime
    
    current_year = datetime.now().year
    newest_content = Content.objects.order_by('-release_date')[:8]
    newest_ids = [content.id for content in newest_content]
    trending_content = Content.objects.filter(
        id__in=newest_ids
    ).annotate(
        average_rating=Avg('ratings__rating_value')
    ).order_by('-average_rating', '-release_date')
    
    for content in trending_content:
        content.is_new_release = (content.release_date.year == current_year)

    recent_content = Content.objects.order_by('-created_at')[:6]
    
    popular_genres = Content.objects.values('genre').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'trending_content': trending_content,
        'recent_content': recent_content,
        'popular_genres': popular_genres,
        'total_content': Content.objects.count(),
        'current_year': current_year,
    }
    return render(request, 'recommendox/home.html', context)


def content_list(request):
    """Browse all content with filters"""
    from django.db.models import Avg, Q
    
    genre = request.GET.get('genre')
    language = request.GET.get('language')
    content_type = request.GET.get('content_type')
    search = request.GET.get('search')
    sort_by = request.GET.get('sort', 'newest') 
  
    content_ids = Content.objects.all().values_list('id', flat=True)
   
    if genre:
        content_ids = content_ids.filter(genre=genre)
    if language:
        content_ids = content_ids.filter(language=language)
    if content_type:
        content_ids = content_ids.filter(content_type=content_type)
   
    if search:
        content_ids = content_ids.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(director__icontains=search) |
            Q(cast__icontains=search)
        )
    
    content_ids = content_ids.distinct()
    content_list = Content.objects.filter(id__in=content_ids)
    if sort_by == 'rating':
        content_list = content_list.annotate(
            rating_avg=Avg('ratings__rating_value')
        ).order_by('-rating_avg', '-release_date')
    elif sort_by == 'oldest':
        content_list = content_list.order_by('release_date')
    elif sort_by == 'title_asc':
        content_list = content_list.order_by('title')
    elif sort_by == 'title_desc':
        content_list = content_list.order_by('-title')
    else:  
        content_list = content_list.order_by('-release_date')
    
    paginator = Paginator(content_list, 12)
    page = request.GET.get('page')
    content = paginator.get_page(page)
    
    genres = Content.objects.values_list('genre', flat=True).distinct()
    languages = Content.objects.values_list('language', flat=True).distinct()
    
    context = {
        'content': content,
        'genres': genres,
        'languages': languages,
        'selected_genre': genre,
        'selected_language': language,
        'selected_type': content_type,
        'search_query': search,
        'sort_by': sort_by,
    }
    return render(request, 'recommendox/content_list.html', context)


def content_detail(request, content_id):
    """Content detail page with prioritized reviews"""
    content = get_object_or_404(Content, id=content_id)
    
    increment_content_views(content)
    
    user_rating = None
    in_watchlist = False
    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(user=request.user, content=content)
        except Rating.DoesNotExist:
            pass
        
        in_watchlist = Watchlist.objects.filter(user=request.user, content=content).exists()
  
    similar_content = Content.objects.filter(
        genre=content.genre
    ).exclude(id=content_id).annotate(
        rating_avg=Avg('ratings__rating_value')
    ).order_by('-rating_avg')[:4]
    
    all_reviews = Review.objects.filter(content=content).select_related('user')
    
    reviewer_reviews = all_reviews.filter(is_verified=True).order_by('-review_date')
    regular_reviews = all_reviews.filter(is_verified=False).order_by('-review_date')
    
    from itertools import chain
    reviews = list(chain(reviewer_reviews, regular_reviews))
    
    context = {
        'content': content,
        'user_rating': user_rating,
        'in_watchlist': in_watchlist,
        'similar_content': similar_content,
        'reviews': reviews,  
    }
    return render(request, 'recommendox/content_detail.html', context)

def increment_content_views(content):
    """Increment view count for content"""
    content.views_count += 1
    content.save(update_fields=['views_count'])
    return content.views_count

def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )
            UserProfile.objects.create(user=user)
            messages.success(request, 'Registration successful! Please login.')
            return redirect('recommendox:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'recommendox/register.html', {'form': form})


def user_login(request):
    """User login"""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('recommendox:user_dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'recommendox/login.html', {'form': form})


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('recommendox:home')


#USER VIEWS
@login_required
def user_dashboard(request):
    """User dashboard"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)  
    user_is_reviewer = is_reviewer(user)

    watchlist = Content.objects.filter(
        id__in=Watchlist.objects.filter(user=user).values_list('content_id', flat=True)
    )[:6]
 
    user_ratings = Rating.objects.filter(user=user).order_by('-rating_date')[:5]   
    user_reviews = Review.objects.filter(user=user).order_by('-review_date')[:5]   
    recommendations = get_personalized_recommendations(user)
    
    context = {
        'user': user,
        'profile': profile,
        'watchlist': watchlist,
        'user_ratings': user_ratings,
        'user_reviews': user_reviews,
        'recommendations': recommendations,
        'is_reviewer': user_is_reviewer,
    }
    return render(request, 'recommendox/user_dashboard.html', context)


@login_required
def manage_watchlist(request):
    """Manage user's watchlist"""
    if request.method == 'POST':
        content_id = request.POST.get('content_id')
        action = request.POST.get('action')
        content = get_object_or_404(Content, id=content_id)
        
        if action == 'add':
            Watchlist.objects.get_or_create(user=request.user, content=content)
            messages.success(request, f'Added "{content.title}" to watchlist!')
        elif action == 'remove':
            Watchlist.objects.filter(user=request.user, content=content).delete()
            messages.success(request, f'Removed "{content.title}" from watchlist!')
    
    return redirect(request.META.get('HTTP_REFERER', 'recommendox:user_dashboard'))


@login_required
def rate_content(request, content_id):
    """Rate content"""
    content = get_object_or_404(Content, id=content_id)
    
    if request.method == 'POST':
        rating_value = request.POST.get('rating')
        if rating_value and 1 <= int(rating_value) <= 5:
            Rating.objects.update_or_create(
                user=request.user,
                content=content,
                defaults={'rating_value': rating_value}
            )
            messages.success(request, f'You rated "{content.title}" {rating_value}/5!')
    
    return redirect('recommendox:content_detail', content_id=content_id)

@login_required
def add_review(request, content_id):
    """Add review for content - Auto-approved for everyone"""
    content = get_object_or_404(Content, id=content_id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment')
        if comment:
            is_reviewer = False
            try:
                is_reviewer = hasattr(request.user.profile, 'reviewer_profile') and request.user.profile.reviewer_profile.is_active
            except:
                pass
   
            review = Review.objects.create(
                user=request.user,
                content=content,
                comment=comment,
                is_approved=True,          
                is_verified=is_reviewer      
            )
          
            messages.success(request, 'Your review has been posted!')
    
    return redirect('recommendox:content_detail', content_id=content_id)

@login_required
def edit_review(request, review_id):
    """Edit user's own review"""
    review = get_object_or_404(Review, id=review_id)
   
    if review.user != request.user:
        messages.error(request, 'You can only edit your own reviews!')
        return redirect('recommendox:content_detail', content_id=review.content.id)
    
    if request.method == 'POST':
        new_comment = request.POST.get('comment')
        if new_comment:
            review.comment = new_comment
          
            is_admin = request.user.is_staff or request.user.is_superuser
            is_reviewer = False
            
            try:
                is_reviewer = hasattr(request.user.profile, 'reviewer_profile') and request.user.profile.reviewer_profile.is_active
            except:
                pass
            
            if not (is_admin or is_reviewer):
                review.is_approved = False
            
            review.save()
            messages.success(request, 'Review updated successfully!')
            return redirect('recommendox:content_detail', content_id=review.content.id)
    
    return render(request, 'recommendox/edit_review.html', {'review': review})


@login_required
def delete_review(request, review_id):
    """Delete user's own review"""
    review = get_object_or_404(Review, id=review_id)
    
    if review.user != request.user and not request.user.is_staff:
        messages.error(request, 'You can only delete your own reviews!')
        return redirect('recommendox:content_detail', content_id=review.content.id)
    
    if request.method == 'POST':
        content_id = review.content.id
        review.delete()
        messages.success(request, 'Review deleted successfully!')
        return redirect('recommendox:content_detail', content_id=content_id)
    
    return render(request, 'recommendox/confirm_delete.html', {'review': review})

@content_creator_required
def creator_dashboard(request):
    """Content Creator Dashboard"""
    user = request.user
   
    creator = None
    try:
        creator = user.profile.creator_profile
    except:
        pass
    recent_content = Content.objects.order_by('-created_at')[:10]
   
    total_content = Content.objects.count()
    recent_count = Content.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
    
    context = {
        'creator': creator,
        'recent_content': recent_content,
        'total_content': total_content,
        'recent_count': recent_count,
    }
    return render(request, 'recommendox/creator_dashboard.html', context)


@content_creator_required
def manage_content(request):
    """Content management for admin and creators"""
    if request.method == 'POST':
        form = ContentForm(request.POST)
        if form.is_valid():
          
            content = form.save()
          
            platform = request.POST.get('ott_platform')
            url = request.POST.get('ott_url')
            is_free = request.POST.get('ott_free') == 'True'
            
            if platform and url: 
                ContentOTT.objects.create(
                    content=content,
                    platform_name=platform,
                    watch_url=url,
                    is_free=is_free
                )
                messages.success(request, f'Content added with OTT platform: {platform}')
            else:
                messages.success(request, 'Content added successfully (no OTT platform)')
            
            return redirect('recommendox:manage_content')
    else:
        form = ContentForm()
    
    content_list = Content.objects.all().order_by('-created_at')
    context = {
        'form': form,
        'content_list': content_list,
    }
    return render(request, 'recommendox/manage_content.html', context)

@staff_member_required 
@content_creator_required  
def edit_content(request, content_id):
    """Edit content - works for both admin and creators"""
    content = get_object_or_404(Content, id=content_id)
    
    from .models import ContentOTT
    ott = ContentOTT.objects.filter(content=content).first()
    
    if request.method == 'POST':
        form = ContentForm(request.POST, instance=content)
        if form.is_valid():
            form.save()
            
            ContentOTT.objects.filter(content=content).delete()
            
            platform = request.POST.get('ott_platform')
            url = request.POST.get('ott_url')
            is_free = request.POST.get('ott_free') == 'True'
            
            if platform and url:
                ContentOTT.objects.create(
                    content=content,
                    platform_name=platform,
                    watch_url=url,
                    is_free=is_free
                )
            
            messages.success(request, 'Content updated successfully!')
            return redirect('recommendox:manage_content')
    else:
        form = ContentForm(instance=content)
    
    context = {
        'form': form,
        'content': content,
        'ott': ott,  
    }
    return render(request, 'recommendox/edit_content.html', context)

@content_creator_required
def delete_content(request, content_id):
    """Delete content"""
    if request.method == 'POST':
        content = get_object_or_404(Content, id=content_id)
        title = content.title
        content.delete()
        messages.success(request, f'"{title}" deleted successfully!')
    
    return redirect('recommendox:manage_content')

#ADMIN VIEWS
@staff_member_required
def admin_dashboard(request):
    """Admin dashboard"""
   
    total_users = User.objects.count()
    total_content = Content.objects.count()
    total_reviews = Review.objects.count()
    pending_reviews = Review.objects.filter(is_approved=False).count()
    approved_reviews = Review.objects.filter(is_approved=True).count()
    total_reviewers = Reviewer.objects.count()
    total_creators = ContentCreator.objects.count()
  
    pending_golden = GoldenUser.objects.filter(verification_status='Pending').count()
    
    recent_content = Content.objects.order_by('-created_at')[:5]
    recent_reviews = Review.objects.order_by('-review_date')[:5]
    
    context = {
        'total_users': total_users,
        'total_content': total_content,
        'total_reviews': total_reviews,
        'pending_reviews': pending_reviews,
        'approved_reviews': approved_reviews,
        'total_reviewers': total_reviewers,
        'total_creators': total_creators,
        'pending_golden': pending_golden,  
        'recent_content': recent_content,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'recommendox/admin_dashboard.html', context)

@staff_member_required
def manage_users(request):
    """User management for admin"""
    search_query = request.GET.get('search', '')
    
    if search_query:
        users = User.objects.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        ).order_by('-date_joined')
    else:
        users = User.objects.all().order_by('-date_joined')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, id=user_id)
        
        if action == 'block':
            user.is_active = False
            user.save()
            messages.success(request, f'User "{user.username}" blocked.')
        elif action == 'unblock':
            user.is_active = True
            user.save()
            messages.success(request, f'User "{user.username}" unblocked.')
        elif action == 'delete':
            username = user.username
            user.delete()
            messages.success(request, f'User "{username}" deleted.')

    for user in users:
        try:
            user.is_reviewer = hasattr(user.profile, 'reviewer_profile') and user.profile.reviewer_profile.is_active
        except:
            user.is_reviewer = False
        
        try:
            user.is_creator = hasattr(user.profile, 'creator_profile') and user.profile.creator_profile.is_active
        except:
            user.is_creator = False
    
    context = {
        'users': users,
        'search_query': search_query,
    }
    return render(request, 'recommendox/manage_users.html', context)


@staff_member_required
def make_reviewer(request, user_id):
    """Upgrade a user to reviewer role"""
    user = get_object_or_404(User, id=user_id)
    profile, created = UserProfile.objects.get_or_create(user=user)
   
    if hasattr(profile, 'reviewer_profile'):
        messages.warning(request, f'{user.username} is already a reviewer!')
    else:
        Reviewer.objects.create(
            user_profile=profile,
            is_active=True
        )
        messages.success(request, f'{user.username} is now a reviewer!')
    
    return redirect('recommendox:manage_users')

@staff_member_required
def fix_admin_reviewer(request):
    """Temporary view to fix admin reviewer status"""
    admin = User.objects.get(username='admin')
    profile, _ = UserProfile.objects.get_or_create(user=admin)
    
    reviewer, created = Reviewer.objects.get_or_create(
        user_profile=profile,
        defaults={'is_active': True}
    )
    
    if created:
        messages.success(request, 'Admin is now a reviewer again!')
    else:
        messages.info(request, 'Admin was already a reviewer.')
    
    return redirect('recommendox:admin_dashboard')

@staff_member_required
def make_creator(request, user_id):
    """Upgrade a user to content creator role"""
    user = get_object_or_404(User, id=user_id)
    profile, created = UserProfile.objects.get_or_create(user=user)
   
    if hasattr(profile, 'creator_profile'):
        messages.warning(request, f'{user.username} is already a creator!')
    else:
        ContentCreator.objects.create(
            user_profile=profile,
            is_active=True
        )
        messages.success(request, f'{user.username} is now a creator!')
    
    return redirect('recommendox:manage_users')

@staff_member_required
def remove_reviewer(request, user_id):
    """Remove reviewer role from a user"""
    user = get_object_or_404(User, id=user_id)
    
    try:
        profile = user.profile
        if hasattr(profile, 'reviewer_profile'):
            profile.reviewer_profile.delete()
            messages.success(request, f'Reviewer role removed from {user.username}.')
        else:
            messages.warning(request, f'{user.username} is not a reviewer.')
    except:
        messages.error(request, 'Error removing reviewer role.')
    
    return redirect('recommendox:manage_users')

@staff_member_required
def remove_creator(request, user_id):
    """Remove creator role from a user"""
    user = get_object_or_404(User, id=user_id)
    
    try:
        profile = user.profile
        if hasattr(profile, 'creator_profile'):
            profile.creator_profile.delete()
            messages.success(request, f'Creator role removed from {user.username}.')
        else:
            messages.warning(request, f'{user.username} is not a creator.')
    except:
        messages.error(request, 'Error removing creator role.')
    
    return redirect('recommendox:manage_users')

@staff_member_required
def admin_manage_reviews(request):
    """Admin can view and delete any review"""
    
    # Get all reviews with filters
    filter_by = request.GET.get('filter', 'all')
    
    if filter_by == 'reviewer':
        reviews = Review.objects.filter(is_verified=True).order_by('-review_date')
    elif filter_by == 'regular':
        reviews = Review.objects.filter(is_verified=False).order_by('-review_date')
    else:
        reviews = Review.objects.all().order_by('-review_date')
    
    # Handle deletion
    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        review = get_object_or_404(Review, id=review_id)
        content_title = review.content.title
        username = review.user.username
        review.delete()
        messages.success(request, f'Review by {username} on "{content_title}" deleted.')
        return redirect('recommendox:admin_manage_reviews')
   
    total_reviews = Review.objects.count()
    reviewer_count = Review.objects.filter(is_verified=True).count()
    regular_count = Review.objects.filter(is_verified=False).count()
    
    context = {
        'reviews': reviews,
        'total_reviews': total_reviews,
        'reviewer_count': reviewer_count,
        'regular_count': regular_count,
        'filter': filter_by,
    }
    return render(request, 'recommendox/admin_manage_reviews.html', context)


#OTT VIEWS
def ott_browse(request):
    """Browse content by OTT platform"""
    platform = request.GET.get('platform', '')
    free_only = request.GET.get('free_only') == 'True'
    
    content_list = Content.objects.filter(ott_platforms__isnull=False).distinct()
    
    if platform:
        content_list = content_list.filter(ott_platforms__platform_name=platform)
    
    if free_only:
        content_list = content_list.filter(ott_platforms__is_free=True)
    paginator = Paginator(content_list, 12)
    page = request.GET.get('page')
    contents = paginator.get_page(page)
    
    context = {
        'page_obj': contents,
        'selected_platform': platform,
        'free_only': free_only,
    }
    return render(request, 'recommendox/ott_browse.html', context)

def is_golden_user(user):
    """Check if user has golden user profile"""
    if not user.is_authenticated:
        return False
    try:
        return hasattr(user.profile, 'golden_profile')
    except:
        return False

def golden_user_required(view_func):
    """Decorator to check if user is golden user"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('recommendox:login')
        
        if request.user.is_staff: 
            return view_func(request, *args, **kwargs)
        
        if is_golden_user(request.user):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'This section is only for verified Golden Users.')
        return redirect('recommendox:user_dashboard')
    return wrapper

@login_required
def become_golden_user(request):
    """Apply to become a golden user"""
    user = request.user
    
    try:
        if hasattr(user.profile, 'golden_profile'):
            golden = user.profile.golden_profile
            if golden.verification_status == 'Pending':
                messages.info(request, 'Your Golden User application is pending verification.')
                return redirect('recommendox:golden_dashboard')
            elif golden.verification_status == 'Verified':
                messages.success(request, 'You are already a verified Golden User!')
                return redirect('recommendox:golden_dashboard')
            elif golden.verification_status == 'Rejected':
                messages.warning(request, 'Your previous application was rejected. You can apply again.')
                golden.delete() 
    except AttributeError:
        pass
    except Exception:
        pass
    
    if request.method == 'POST':
        profession = request.POST.get('profession')
        bio = request.POST.get('bio')
        years_experience = request.POST.get('years_experience', 0)
        company = request.POST.get('company', '')
        website = request.POST.get('website', '')
        notable_works = request.POST.get('notable_works', '')
        awards = request.POST.get('awards', '')

        social_media = {
            'twitter': request.POST.get('twitter', ''),
            'instagram': request.POST.get('instagram', ''),
            'linkedin': request.POST.get('linkedin', ''),
            'imdb': request.POST.get('imdb', ''),
        }
        
        profile_image = request.FILES.get('profile_image')
        cover_image = request.FILES.get('cover_image')
        verification_docs = request.FILES.get('verification_docs')
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if user.is_staff or user.is_superuser:
            verification_status = 'Verified'
            from django.utils import timezone
            verified_at = timezone.now()
            verified_by = user 
        else:
            verification_status = 'Pending'
            verified_at = None
            verified_by = None
        
        golden_user = GoldenUser.objects.create(
            user_profile=profile,
            profession=profession,
            bio=bio,
            years_of_experience=years_experience,
            company=company,
            website=website,
            social_media_links=social_media,
            notable_works=notable_works,
            awards=awards,
            profile_image=profile_image,
            cover_image=cover_image,
            verification_documents=verification_docs,
            verification_status=verification_status,
            verified_at=verified_at,
            verified_by=verified_by,
        )
        
        if verification_status == 'Verified':
            messages.success(request, 'You are now a verified Golden User!')
        else:
            messages.success(request, 'Your Golden User application has been submitted for verification!')
            
        return redirect('recommendox:golden_dashboard')
    
    # GET request - show application form
    professions = GoldenUser.PROFESSION_CHOICES
    return render(request, 'recommendox/become_golden.html', {'professions': professions})

@login_required
@golden_user_required
def golden_dashboard(request):
    """Golden User Dashboard - New Design"""
    user = request.user
    golden = user.profile.golden_profile
    profession = golden.profession
    user_name = user.get_full_name() or user.username
    
    if profession in ['Actor', 'Actress']:
        my_content = Content.objects.filter(cast__icontains=user_name)
    elif profession == 'Director':
        my_content = Content.objects.filter(director__icontains=user_name)
    elif profession == 'Producer':
        my_content = Content.objects.filter(
            Q(director__icontains=user_name) |
            Q(description__icontains=f"produced by {user_name}") |
            Q(description__icontains=f"producer {user_name}")
        )
    elif profession == 'Writer':
        my_content = Content.objects.filter(
            Q(director__icontains=user_name) |
            Q(description__icontains=f"written by {user_name}") |
            Q(description__icontains=f"writer {user_name}")
        )
    elif profession in ['Critic', 'Journalist']:
        my_content = None  
        my_reviews = Review.objects.filter(user=user).order_by('-review_date')[:10]
    else:
        my_content = Content.objects.none()
    
    my_content_ids = my_content.values_list('id', flat=True) if my_content else []
    
    
    my_stats = {
        'total_content': my_content.count() if my_content else 0,
        'total_reviews': Review.objects.filter(content__in=my_content_ids).count() if my_content_ids else 0,
        'avg_rating': Rating.objects.filter(content__in=my_content_ids).aggregate(avg=Avg('rating_value'))['avg'] or 0,
    }
    
    
    if profession in ['Critic', 'Journalist']:
        my_genres = Content.objects.values('genre').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        my_genre_list = [g['genre'] for g in my_genres]
    else:
        my_genre_list = list(my_content.values_list('genre', flat=True).distinct())
    
    
    trending_in_genre = Content.objects.filter(
        genre__in=my_genre_list
    ).exclude(
        id__in=my_content_ids
    ).annotate(
        rating_avg=Avg('ratings__rating_value')
    ).order_by('-rating_avg')[:8]
    
    
    genre_stats = Content.objects.values('genre').annotate(
        avg_rating=Avg('ratings__rating_value')
    ).order_by('genre')
    
    
    ott_stats = ContentOTT.objects.values('platform_name').annotate(
        avg_rating=Avg('content__ratings__rating_value')
    ).order_by('-avg_rating')
    
    
    if my_content_ids:
        recent_feedback = Review.objects.filter(
            content__in=my_content_ids
        ).select_related('user', 'content').order_by('-review_date')[:10]
    else:
        recent_feedback = []
    
    context = {
        'golden': golden,
        'profession': profession,
        'my_content': my_content,
        'my_reviews': my_reviews if profession in ['Critic', 'Journalist'] else None,
        'my_stats': my_stats,
        'trending_in_genre': trending_in_genre,
        'genre_stats': genre_stats,
        'ott_stats': ott_stats,
        'recent_feedback': recent_feedback,
    }
    return render(request, 'recommendox/golden_dashboard.html', context)

@golden_user_required
def golden_content_analytics(request, content_id):
    """Detailed analytics for specific content"""
    content = get_object_or_404(Content, id=content_id)
   
    golden = request.user.profile.golden_profile
    golden.increment_content_views()
    
    increment_content_views(content)

    rating_stats = Rating.objects.filter(content=content).values('rating_value').annotate(
        count=Count('id')
    ).order_by('rating_value')
    
    reviews = Review.objects.filter(content=content, is_approved=True).select_related('user')
    
    ott_availability = ContentOTT.objects.filter(content=content)
    
    similar_content = Content.objects.filter(genre=content.genre).exclude(id=content_id)[:5]
    
    context = {
        'content': content,
        'rating_stats': rating_stats,
        'total_ratings': Rating.objects.filter(content=content).count(),
        'avg_rating': content.avg_rating,
        'reviews': reviews,
        'total_reviews': reviews.count(),
        'total_views': content.views_count,
        'ott_availability': ott_availability,
        'similar_content': similar_content,
        'golden': golden,
    }
    return render(request, 'recommendox/golden_content_analytics.html', context)

@staff_member_required
def verify_golden_users(request):
    """Admin view to verify golden user applications """
    
    status_filter = request.GET.get('status', 'Pending')
    
    base_qs = GoldenUser.objects.select_related('user_profile__user')
    
    if status_filter == 'All':
        applications = base_qs.all()
    else:
        applications = base_qs.filter(verification_status=status_filter)
   
    if request.method == 'POST':
        golden_id = request.POST.get('golden_id')
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if not golden_id or not action:
            messages.error(request, 'Invalid request.')
            return redirect('recommendox:verify_golden_users')
        
        golden = get_object_or_404(GoldenUser, id=golden_id)
        
        if action == 'verify':
            golden.verification_status = 'Verified'
            golden.verified_at = timezone.now()
            golden.verified_by = request.user
            golden.verification_notes = notes
            messages.success(request, f'{golden.user_profile.user.username} is now a verified Golden User!')
            
        elif action == 'reject':
            golden.verification_status = 'Rejected'
            golden.verification_notes = notes
            messages.warning(request, f'Application for {golden.user_profile.user.username} rejected.')
            
        else:
            messages.error(request, 'Unknown action.')
            return redirect('recommendox:verify_golden_users')
        
        golden.save()
        return redirect('recommendox:verify_golden_users')
  
    pending_count = GoldenUser.objects.filter(verification_status='Pending').count()
    verified_count = GoldenUser.objects.filter(verification_status='Verified').count()
    rejected_count = GoldenUser.objects.filter(verification_status='Rejected').count()
    total_count = GoldenUser.objects.count()
    
    context = {
        'applications': applications,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'verified_count': verified_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
    }
    return render(request, 'recommendox/verify_golden.html', context)
