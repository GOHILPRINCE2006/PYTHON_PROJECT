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

# recommendox/admin.py - Update GoldenUserAdmin

@admin.register(GoldenUser)
class GoldenUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile', 'profession', 'verification_status', 'years_of_experience', 'created_at')
    list_filter = ('verification_status', 'profession')
    search_fields = ('user_profile__user__username', 'profession', 'company')
    readonly_fields = ('created_at', 'updated_at', 'total_content_views', 'total_reviews_given')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_profile',)
        }),
        ('Professional Details', {
            'fields': ('profession', 'bio', 'years_of_experience', 'company', 'website')
        }),
        ('Social Media', {
            'fields': ('social_media_links',),
            'classes': ('wide',),
        }),
        ('Portfolio', {
            'fields': ('notable_works', 'awards')
        }),
        ('Media', {
            'fields': ('profile_image', 'cover_image')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verification_documents', 'verification_notes', 'verified_at', 'verified_by')
        }),
        ('Statistics', {
            'fields': ('total_content_views', 'total_reviews_given', 'followers_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['verify_selected', 'reject_selected']
    
    def verify_selected(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            verification_status='Verified',
            verified_at=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f"{queryset.count()} Golden Users verified.")
    verify_selected.short_description = "Verify selected Golden Users"
    
    def reject_selected(self, request, queryset):
        queryset.update(verification_status='Rejected')
        self.message_user(request, f"{queryset.count()} Golden Users rejected.")
    reject_selected.short_description = "Reject selected Golden Users"

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