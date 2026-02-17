# recommendox/admin.py
from django.contrib import admin
from .models import (
    Content, Season, Episode, UserProfile, GoldenUser, 
    Watchlist, Rating, Review, Analytics, Message, Reviewer, ContentOTT, ContentCreator
)

# Register your models here
@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content_type', 'genre', 'language', 'release_date')
    list_filter = ('content_type', 'genre', 'language')
    search_fields = ('title', 'description', 'director', 'cast')
    ordering = ('-created_at',)

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'season_number', 'title')
    list_filter = ('content',)

@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'season', 'episode_number', 'title', 'duration')
    list_filter = ('season__content',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_premium', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(GoldenUser)
class GoldenUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile', 'subscription_status', 'is_verified')
    list_filter = ('subscription_status', 'is_verified')

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'added_at')
    list_filter = ('user',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'rating_value', 'rating_date')
    list_filter = ('rating_value',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):  # Make sure this is here
    list_display = ('id', 'user', 'content', 'is_approved', 'is_verified', 'review_date')
    list_filter = ('is_approved', 'is_verified', 'review_date')
    search_fields = ('comment', 'user__username', 'content__title')
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} reviews approved.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        queryset.delete()
        self.message_user(request, f"{queryset.count()} reviews rejected.")
    reject_reviews.short_description = "Reject selected reviews"

@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'total_views', 'popularity_score', 'last_updated')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'subject', 'sent_at', 'is_read')
    list_filter = ('is_read', 'sent_at')

@admin.register(Reviewer)
class ReviewerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile', 'is_active', 'verified_at', 'expertise_area')
    list_filter = ('is_active',)

@admin.register(ContentOTT)
class ContentOTTAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'platform_name', 'is_free')
    list_filter = ('platform_name', 'is_free')
    search_fields = ('content__title',)


@admin.register(ContentCreator)
class ContentCreatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile', 'is_active', 'verified_at', 'total_contents_added')
    list_filter = ('is_active',)
    search_fields = ('user_profile__user__username',)