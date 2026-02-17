# recommendox/views.py - FIXED IMPORTS
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
from .models import (
    Content, UserProfile, GoldenUser, Watchlist, 
    Rating, Review, Analytics, Message, Reviewer, ContentOTT, ContentCreator
)
from .forms import UserRegistrationForm, ContentForm, ReviewForm


# ==================== HELPER FUNCTIONS & DECORATORS (MUST BE FIRST) ====================

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
        
        if request.user.is_staff:  # Admin can also access
            return view_func(request, *args, **kwargs)
        
        if is_content_creator(request.user):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'You need to be a verified content creator to access this page.')
        return redirect('recommendox:user_dashboard')
    return wrapper


def get_personalized_recommendations(user):
    """Generate personalized recommendations based on user activity"""
    recommendations = []
    
    # Get user's favorite genres from ratings
    user_ratings = Rating.objects.filter(user=user)
    if user_ratings.exists():
        # Find highest rated genres
        from collections import Counter
        genre_counter = Counter()
        
        for rating in user_ratings:
            if rating.rating_value >= 4:  # Only consider high ratings
                genre_counter[rating.content.genre] += rating.rating_value
        
        if genre_counter:
            # Get top 2 genres
            top_genres = [genre for genre, count in genre_counter.most_common(2)]
            
            # Recommend content from top genres not yet rated
            for genre in top_genres:
                genre_content = Content.objects.filter(
                    genre=genre
                ).exclude(
                    id__in=user_ratings.values_list('content_id', flat=True)
                ).order_by('-ratings__rating_value')[:3]
                
                recommendations.extend(list(genre_content))
    
    # If not enough recommendations, add popular content
    if len(recommendations) < 6:
        additional = Content.objects.exclude(
            id__in=[c.id for c in recommendations]
        ).order_by('-ratings__rating_value')[:6-len(recommendations)]
        
        recommendations.extend(list(additional))
    
    return recommendations[:6]  # Return max 6 recommendations


# ==================== PUBLIC VIEWS ====================

def home(request):
    """Public home page"""
    from django.db.models import Avg
    
    # Trending content (highest rated)
    trending_content = Content.objects.annotate(
        average_rating=Avg('ratings__rating_value')
    ).order_by('-average_rating')[:8]
    
    # Recently added
    recent_content = Content.objects.order_by('-created_at')[:6]
    
    # Popular genres
    popular_genres = Content.objects.values('genre').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'trending_content': trending_content,
        'recent_content': recent_content,
        'popular_genres': popular_genres,
        'total_content': Content.objects.count(),
    }
    return render(request, 'recommendox/home.html', context)


def content_list(request):
    """Browse all content with filters"""
    content_list = Content.objects.all()
    
    # Filtering
    genre = request.GET.get('genre')
    language = request.GET.get('language')
    content_type = request.GET.get('content_type')
    search = request.GET.get('search')
    
    if genre:
        content_list = content_list.filter(genre=genre)
    if language:
        content_list = content_list.filter(language=language)
    if content_type:
        content_list = content_list.filter(content_type=content_type)
    if search:
        content_list = content_list.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(director__icontains=search) |
            Q(cast__icontains=search)
        )
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    content_list = content_list.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(content_list, 12)
    page = request.GET.get('page')
    content = paginator.get_page(page)
    
    # Get unique values for filters
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
    }
    return render(request, 'recommendox/content_list.html', context)


def content_detail(request, content_id):
    """Content detail page"""
    content = get_object_or_404(Content, id=content_id)
    
    # Get user's rating if logged in
    user_rating = None
    in_watchlist = False
    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(user=request.user, content=content)
        except Rating.DoesNotExist:
            pass
        
        in_watchlist = Watchlist.objects.filter(user=request.user, content=content).exists()
    
    # Get similar content (same genre)
    similar_content = Content.objects.filter(
        genre=content.genre
    ).exclude(id=content_id).annotate(
        avg_rating=Avg('ratings__rating_value')
    ).order_by('-avg_rating')[:4]
    
    # Get approved reviews
    reviews = Review.objects.filter(content=content, is_approved=True).order_by('-review_date')
    
    context = {
        'content': content,
        'user_rating': user_rating,
        'in_watchlist': in_watchlist,
        'similar_content': similar_content,
        'reviews': reviews,
    }
    return render(request, 'recommendox/content_detail.html', context)


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


# ==================== USER VIEWS ====================

@login_required
def user_dashboard(request):
    """User dashboard"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Check if user is reviewer
    user_is_reviewer = is_reviewer(user)
    
    # User's watchlist
    watchlist = Content.objects.filter(
        id__in=Watchlist.objects.filter(user=user).values_list('content_id', flat=True)
    )[:6]
    
    # User's ratings
    user_ratings = Rating.objects.filter(user=user).order_by('-rating_date')[:5]
    
    # User's reviews
    user_reviews = Review.objects.filter(user=user).order_by('-review_date')[:5]
    
    # Personalized recommendations
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
    """Add review for content"""
    content = get_object_or_404(Content, id=content_id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment')
        if comment:
            # Check if user is reviewer
            user_is_reviewer = False
            try:
                user_is_reviewer = hasattr(request.user.profile, 'reviewer_profile') and request.user.profile.reviewer_profile.is_active
            except:
                pass
            
            review = Review.objects.create(
                user=request.user,
                content=content,
                comment=comment,
                is_approved=user_is_reviewer,  # Auto-approve for reviewers
                is_verified=user_is_reviewer   # Mark as verified for reviewers
            )
            
            if user_is_reviewer:
                messages.success(request, 'Your review has been posted!')
            else:
                messages.success(request, 'Your review has been submitted for moderation.')
    
    return redirect('recommendox:content_detail', content_id=content_id)


@login_required
def edit_review(request, review_id):
    """Edit user's own review"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if user owns this review
    if review.user != request.user:
        messages.error(request, 'You can only edit your own reviews!')
        return redirect('recommendox:content_detail', content_id=review.content.id)
    
    if request.method == 'POST':
        new_comment = request.POST.get('comment')
        if new_comment:
            review.comment = new_comment
            # If reviewer, keep approved; if normal user, reset to pending
            if not is_reviewer(request.user):
                review.is_approved = False
            review.save()
            messages.success(request, 'Review updated successfully!')
            return redirect('recommendox:content_detail', content_id=review.content.id)
    
    return render(request, 'recommendox/edit_review.html', {'review': review})


@login_required
def delete_review(request, review_id):
    """Delete user's own review"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if user owns this review or is admin
    if review.user != request.user and not request.user.is_staff:
        messages.error(request, 'You can only delete your own reviews!')
        return redirect('recommendox:content_detail', content_id=review.content.id)
    
    if request.method == 'POST':
        content_id = review.content.id
        review.delete()
        messages.success(request, 'Review deleted successfully!')
        return redirect('recommendox:content_detail', content_id=content_id)
    
    return render(request, 'recommendox/confirm_delete.html', {'review': review})


# ==================== CONTENT CREATOR VIEWS ====================

@content_creator_required
def creator_dashboard(request):
    """Content Creator Dashboard"""
    user = request.user
    
    # Get creator profile
    creator = None
    try:
        creator = user.profile.creator_profile
    except:
        pass
    
    # Get content added by this creator (if you track this)
    # You might need to add a 'added_by' field to Content model
    # For now, show all content
    recent_content = Content.objects.order_by('-created_at')[:10]
    
    # Get statistics
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
            # Save the content first
            content = form.save()
            
            # Save ONE OTT platform
            platform = request.POST.get('ott_platform')
            url = request.POST.get('ott_url')
            is_free = request.POST.get('ott_free') == 'True'
            
            if platform and url:  # Only save if both platform and URL are provided
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


@content_creator_required
def edit_content(request, content_id):
    """Edit content"""
    content = get_object_or_404(Content, id=content_id)
    
    if request.method == 'POST':
        form = ContentForm(request.POST, instance=content)
        if form.is_valid():
            form.save()
            
            # Update OTT platform (delete old, create new)
            ContentOTT.objects.filter(content=content).delete()
            
            # Create new OTT entry
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
        # Get existing OTT data for the form
        ott = ContentOTT.objects.filter(content=content).first()
    
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


# ==================== ADMIN VIEWS ====================

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard"""
    # Statistics
    total_users = User.objects.count()
    total_content = Content.objects.count()
    total_reviews = Review.objects.count()
    pending_reviews = Review.objects.filter(is_approved=False).count()
    approved_reviews = Review.objects.filter(is_approved=True).count()
    total_reviewers = Reviewer.objects.count()
    total_creators = ContentCreator.objects.count()
    
    # Recent activity
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
    
    # Get reviewer status and creator status for each user
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
    
    # Check if already reviewer
    try:
        if profile.reviewer_profile:
            messages.warning(request, f'{user.username} is already a reviewer!')
            return redirect('recommendox:manage_users')
    except:
        # Create reviewer profile
        Reviewer.objects.create(
            user_profile=profile,
            is_active=True
        )
        messages.success(request, f'{user.username} is now a reviewer! Their reviews will be auto-approved.')
    
    return redirect('recommendox:manage_users')


@staff_member_required
def make_creator(request, user_id):
    """Upgrade a user to content creator role"""
    user = get_object_or_404(User, id=user_id)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Check if already creator
    try:
        if profile.creator_profile:
            messages.warning(request, f'{user.username} is already a content creator!')
            return redirect('recommendox:manage_users')
    except:
        # Create creator profile
        ContentCreator.objects.create(
            user_profile=profile,
            is_active=True
        )
        messages.success(request, f'{user.username} is now a content creator! They can add/edit/delete content.')
    
    return redirect('recommendox:manage_users')


@staff_member_required
def moderate_reviews(request):
    """Review moderation for admin"""
    # Get filter from request
    filter_type = request.GET.get('filter', 'pending')
    
    if filter_type == 'pending':
        reviews = Review.objects.filter(is_approved=False).order_by('-review_date')
    elif filter_type == 'approved':
        reviews = Review.objects.filter(is_approved=True).order_by('-review_date')
    else:
        reviews = Review.objects.all().order_by('-review_date')
    
    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        action = request.POST.get('action')
        review = get_object_or_404(Review, id=review_id)
        
        if action == 'approve':
            review.is_approved = True
            review.save()
            messages.success(request, 'Review approved successfully!')
        elif action == 'reject':
            review.delete()
            messages.success(request, 'Review rejected and deleted!')
        elif action == 'delete':
            review.delete()
            messages.success(request, 'Review deleted successfully!')
        
        return redirect('recommendox:moderate_reviews')
    
    # Get counts for dashboard
    pending_count = Review.objects.filter(is_approved=False).count()
    approved_count = Review.objects.filter(is_approved=True).count()
    total_count = Review.objects.count()
    
    context = {
        'reviews': reviews,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_count': total_count,
        'filter_type': filter_type,
    }
    return render(request, 'recommendox/moderate_reviews.html', context)


# ==================== OTT VIEWS ====================

def ott_browse(request):
    """Browse content by OTT platform"""
    platform = request.GET.get('platform', '')
    free_only = request.GET.get('free_only') == 'True'
    
    # Get all content that has OTT platforms
    content_list = Content.objects.filter(ott_platforms__isnull=False).distinct()
    
    if platform:
        # Filter by specific platform
        content_list = content_list.filter(ott_platforms__platform_name=platform)
    
    if free_only:
        # Filter by free content
        content_list = content_list.filter(ott_platforms__is_free=True)
    
    # Pagination
    paginator = Paginator(content_list, 12)
    page = request.GET.get('page')
    contents = paginator.get_page(page)
    
    context = {
        'page_obj': contents,
        'selected_platform': platform,
        'free_only': free_only,
    }
    return render(request, 'recommendox/ott_browse.html', context)