# recommendox/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Content(models.Model):
    GENRE_CHOICES = [
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Horror', 'Horror'),
        ('Sci-Fi', 'Sci-Fi'),
        ('Romance', 'Romance'),
        ('Thriller', 'Thriller'),
        ('Animation', 'Animation'),
        ('Documentary', 'Documentary'),
        ('Fantasy', 'Fantasy'),
    ]
    
    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Hindi', 'Hindi'),
        ('Spanish', 'Spanish'),
        ('French', 'French'),
        ('Japanese', 'Japanese'),
        ('Korean', 'Korean'),
        ('Other', 'Other'),
    ]
    
    CONTENT_TYPES = [  
        ('Movie', 'Movie'),
        ('Web Series', 'Web Series'),
        ('TV Show', 'TV Show'),
        ('Documentary', 'Documentary'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES)
    language = models.CharField(max_length=50, choices=LANGUAGE_CHOICES)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default='Movie')  # FIXED: CONTENT_TYPES
    release_date = models.DateField()
    duration = models.CharField(max_length=20, blank=True, null=True)  # "2h 30m" or "Season 1"
    director = models.CharField(max_length=100, blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    poster_url = models.URLField(max_length=10000, blank=True, null=True)
    trailer_url = models.URLField(max_length=10000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Calculated field
    @property
    def avg_rating(self):
        ratings = self.ratings.all()
        if ratings:
            return sum([r.rating_value for r in ratings]) / len(ratings)
        return 0
    
    def __str__(self):
        return f"{self.title} ({self.release_date.year})"
    
    def get_details(self):
        return {
            'title': self.title,
            'genre': self.genre,
            'language': self.language,
            'release_date': self.release_date,
            'avg_rating': self.avg_rating,
            'description': self.description[:100] + '...' if len(self.description) > 100 else self.description
        }
    
    def get_duration_display(self):  
        """Return formatted duration with appropriate icon"""
        if not self.duration:
            return "N/A"
        
        if self.content_type == 'Movie':
            return f"⏱️ {self.duration}"
        elif self.content_type in ['Web Series', 'TV Show']:
            if 'Season' in self.duration:
                return f"📺 {self.duration}"
            return f"📺 {self.duration}"
        else:
            return self.duration

class Season(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='seasons')
    season_number = models.IntegerField()
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['content', 'season_number'] 
    
    def __str__(self):
        return f"{self.content.title} - Season {self.season_number}"
    
    @property
    def episode_count(self):
        return self.episodes.count()
    
    @property
    def total_duration(self):
        return self.episodes.aggregate(total=models.Sum('duration'))['total'] or 0

class Episode(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='episodes')
    episode_number = models.IntegerField()
    title = models.CharField(max_length=200)
    duration = models.IntegerField(help_text="Duration in minutes")
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['season', 'episode_number']  # ADD THIS
        ordering = ['episode_number']  # ADD THIS
    
    def __str__(self):
        return f"S{self.season.season_number}E{self.episode_number}: {self.title}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    favorite_genres = models.CharField(max_length=500, blank=True, null=True)
    preferred_languages = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.username
    
    def update_profile(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.save()

# recommendox/models.py - Add/Update GoldenUser model

class GoldenUser(models.Model):
    """Golden User - Industry professional with verified status"""
    
    PROFESSION_CHOICES = [
        ('Actor', 'Actor'),
        ('Director', 'Director'),
        ('Producer', 'Producer'),
        ('Writer', 'Writer'),
        ('Cinematographer', 'Cinematographer'),
        ('Editor', 'Editor'),
        ('Music Director', 'Music Director'),
        ('Critic', 'Film Critic'),
        ('Journalist', 'Entertainment Journalist'),
        ('Other', 'Other'),
    ]
    
    VERIFICATION_STATUS = [
        ('Pending', 'Pending Verification'),
        ('Verified', 'Verified Professional'),
        ('Rejected', 'Verification Rejected'),
    ]
    
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='golden_profile')
    
    # Professional details
    profession = models.CharField(max_length=50, choices=PROFESSION_CHOICES)
    bio = models.TextField(max_length=1000, blank=True, null=True, help_text="Your professional background")
    years_of_experience = models.IntegerField(default=0)
    company = models.CharField(max_length=200, blank=True, null=True)
    website = models.URLField(max_length=500, blank=True, null=True)
    social_media_links = models.JSONField(default=dict, blank=True, help_text="JSON of social media URLs")
    
    # Profile media
    profile_image = models.ImageField(upload_to='golden_profiles/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='golden_covers/', blank=True, null=True)
    
    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='Pending')
    verification_documents = models.FileField(upload_to='verification_docs/', blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True, help_text="Admin notes on verification")
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_golden_users')
    
    # Professional portfolio
    notable_works = models.TextField(blank=True, null=True, help_text="List of notable works/projects")
    awards = models.TextField(blank=True, null=True, help_text="Awards and recognitions")
    
    # Stats
    total_content_views = models.IntegerField(default=0)
    total_reviews_given = models.IntegerField(default=0)
    followers_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Golden User: {self.user_profile.user.username} - {self.profession}"
    
    def is_verified(self):
        return self.verification_status == 'Verified'
    
    def get_verification_badge(self):
        if self.is_verified():
            return '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Verified Professional</span>'
        return '<span class="badge bg-warning"><i class="fas fa-clock"></i> Pending Verification</span>'
    
    def increment_content_views(self):
        self.total_content_views += 1
        self.save()
    
    def increment_reviews_given(self):
        self.total_reviews_given += 1
        self.save()
    
    class Meta:
        permissions = [
            ("verify_golden_user", "Can verify golden users"),
            ("view_golden_analytics", "Can view golden user analytics"),
        ]

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='in_watchlists')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'content']
        ordering = ['-added_at']  # ADD THIS
    
    def __str__(self):
        return f"{self.user.username} - {self.content.title}"

class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='ratings')
    rating_value = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    rating_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'content']
        ordering = ['-rating_date']  
    
    def __str__(self):
        return f"{self.user.username} rated {self.content.title}: {self.rating_value}/5"


class Review(models.Model):
    """User reviews for content"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='reviews')
    comment = models.TextField()
    review_date = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False) 
    
    class Meta:
        ordering = ['-review_date']
        # unique_together = ['user', 'content']  # One review per user per content
    
    def __str__(self):
        return f"Review by {self.user.username} on {self.content.title}"
    
    def edit_review(self, new_comment):
        self.comment = new_comment
        self.save()

class Reviewer(models.Model):
    """Special user type whose reviews are auto-approved"""
    user_profile = models.OneToOneField('UserProfile', on_delete=models.CASCADE, related_name='reviewer_profile')
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    expertise_area = models.CharField(max_length=200, blank=True, null=True)  # e.g., "Action Movies", "Sci-Fi"
    
    def __str__(self):
        return f"Reviewer: {self.user_profile.user.username}"
    
    class Meta:
        permissions = [
            ("auto_approve_reviews", "Can auto-approve reviews"),
        ]

class Analytics(models.Model):
    content = models.OneToOneField(Content, on_delete=models.CASCADE, related_name='content_analytics')
    total_views = models.IntegerField(default=0)
    popularity_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.content.title}"
    
    def update_views(self):  # ADD THIS
        self.total_views += 1
        self.save()


class ContentOTT(models.Model):
    """Simple OTT availability for content"""
    OTT_CHOICES = [
        ('Netflix', 'Netflix'),
        ('Amazon Prime', 'Amazon Prime Video'),
        ('Disney+', 'Disney+ Hotstar'),
        ('SonyLIV', 'SonyLIV'),
        ('Zee5', 'ZEE5'),
        ('JioCinema', 'JioCinema'),
        ('Other', 'Other'),
    ]
    
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='ott_platforms')
    platform_name = models.CharField(max_length=50, choices=OTT_CHOICES)
    watch_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to watch this content")
    is_free = models.BooleanField(default=False, help_text="Is it free?")
    
    class Meta:
        unique_together = ['content', 'platform_name']  # One platform per content
    
    def __str__(self):
        return f"{self.content.title} on {self.platform_name}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-sent_at']  # ADD THIS
    
    def __str__(self):
        return f"Message from {self.sender.username}: {self.subject}"
    
    def mark_as_read(self):  # ADD THIS
        self.is_read = True
        self.save()

class ContentCreator(models.Model):
    """Content Creator - can add/edit/delete content like admin"""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='creator_profile')
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    expertise = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Movie Reviewer, Series Expert")
    total_contents_added = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Content Creator: {self.user_profile.user.username}"
    
    def increment_content_count(self):
        self.total_contents_added += 1
        self.save()
    
    class Meta:
        permissions = [
            ("can_manage_content", "Can add, edit, delete content"),
        ]