# Daily New Word Target Feature

## 📋 Overview

This feature allows users to configure their daily learning targets with a new `daily_new_word_target` field that specifically controls how many **new words** are introduced per day, separate from review words.

### 🎯 Key Features

- **Pro-only Customization**: Only Pro users can modify their daily new word target (5-100 words)
- **Free User Default**: Free users are locked at 20 new words per day
- **Separate from Reviews**: Learning/review words are shown separately and not limited by this setting
- **Backend Validation**: Server-side enforcement prevents free users from changing the setting
- **Admin Visibility**: Admin panel shows each user's target and effective values

## 🔧 Implementation Details

### Backend Changes

#### 1. Model Updates (`core/models.py`)

```python
class UserProfile(models.Model):
    # ... existing fields ...
    daily_new_word_target = models.PositiveIntegerField(
        default=20, 
        help_text="Number of new words introduced per day (Pro customizable)"
    )
    
    def can_modify_daily_new_word_target(self):
        """Check if user can modify daily new word target (Pro only)."""
        return self.is_pro_active()
    
    def get_effective_daily_new_word_target(self):
        """Get the effective daily new word target."""
        if not self.is_pro_active():
            return 20  # Free users always get 20
        return self.daily_new_word_target
```

#### 2. API Updates (`core/api_views.py`)

- **New Endpoint**: `GET/PATCH /api/profile/` for user profile management
- **Updated Logic**: `_get_next_word()` now uses `daily_new_word_target` for NEW words only
- **Validation**: Pro-only enforcement with proper error messages

#### 3. Settings View Updates (`core/views.py`)

- Added handling for `daily_new_word_target` form submission
- Pro-only validation with user feedback messages
- Template context includes profile object for permission checks

### Frontend Changes

#### 1. Settings Page (`core/templates/core/settings.html`)

```html
<div class="relative">
    <label for="id_daily_new_word_target" class="block text-lg font-medium text-gray-700">
        Daily New Word Target
        {% if not user_profile.can_modify_daily_new_word_target %}
        <span class="inline-flex items-center px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded-full ml-2">
            Pro Only
        </span>
        {% endif %}
    </label>
    
    <input type="number" name="daily_new_word_target" 
           value="{{ user_profile.daily_new_word_target }}" 
           min="5" max="100"
           {% if not user_profile.can_modify_daily_new_word_target %}disabled{% endif %}
           class="...">
    
    {% if not user_profile.can_modify_daily_new_word_target %}
    <div class="absolute inset-0 flex items-center justify-center">
        <div class="bg-white bg-opacity-90 px-2 py-1 rounded text-xs text-orange-600 font-medium">
            <a href="/upgrade/" class="hover:text-orange-800 underline">Upgrade to Pro</a> to customize
        </div>
    </div>
    {% endif %}
</div>
```

#### 2. Admin Panel Enhancements (`core/admin.py`)

- New column: "Effective Daily New Words" showing actual vs. set values
- Color-coded indicators for Pro vs. Free users
- Filter by `daily_new_word_target` values

### API Endpoints

#### GET `/api/profile/`

Returns user profile information including:

```json
{
  "user": {
    "id": 2,
    "username": "testuser",
    "email": "user@example.com"
  },
  "profile": {
    "is_pro": true,
    "is_pro_active": true,
    "daily_new_word_target": 35,
    "effective_daily_new_word_target": 35,
    "can_modify_daily_new_word_target": true
  }
}
```

#### PATCH `/api/profile/`

Update profile settings (Pro only for `daily_new_word_target`):

**Request:**
```json
{
  "daily_new_word_target": 50
}
```

**Success Response (Pro user):**
```json
{
  "status": "success",
  "changes": {
    "daily_new_word_target": {
      "old": 20,
      "new": 50
    }
  },
  "errors": {},
  "profile": {
    "daily_new_word_target": 50,
    "effective_daily_new_word_target": 50,
    "can_modify_daily_new_word_target": true
  }
}
```

**Error Response (Free user):**
```json
{
  "status": "error",
  "changes": {},
  "errors": {
    "daily_new_word_target": "Upgrade to Pro to customize daily new word target"
  },
  "profile": {
    "daily_new_word_target": 20,
    "effective_daily_new_word_target": 20,
    "can_modify_daily_new_word_target": false
  }
}
```

## 🚀 Usage

### For Users

1. **Pro Users**:
   - Visit Settings page
   - Adjust "Daily New Word Target" slider/input (5-100)
   - Changes are saved immediately
   - Affects only NEW words, not reviews

2. **Free Users**:
   - See the setting but cannot modify it
   - Fixed at 20 new words per day
   - Upgrade prompts shown
   - All other settings remain customizable

### For Admins

1. **User Management**:
   - View each user's target in the admin panel
   - See effective vs. set values
   - Filter users by target values
   - Track Pro vs. Free usage patterns

2. **Debugging**:
   - Use the "Effective Daily New Words" column
   - Check color-coded indicators
   - Monitor target compliance

## 🧪 Testing

Run the comprehensive test suite:

```bash
./test_daily_new_word_target.sh
```

### Test Coverage

- ✅ Pro user customization (5-100 range)
- ✅ Free user restriction enforcement
- ✅ Boundary value validation
- ✅ API authentication and authorization
- ✅ Next word API integration
- ✅ Frontend permission handling
- ✅ Admin panel visibility

### Manual Testing

1. **Frontend**: Visit `/settings/` with Pro and Free accounts
2. **API**: Use the test script to validate all endpoints
3. **Admin**: Check `/admin/core/userprofile/` for proper display

## 📊 Business Logic

### Word Learning Flow

1. **Daily Review Session**:
   - Review words (LEARNING state) are shown without limit
   - NEW words are limited by `daily_new_word_target`
   - FREE users: max 20 new words/day
   - PRO users: customizable 5-100 new words/day

2. **Progress Tracking**:
   - `words_learned_today` tracks total progress
   - Resets daily via `check_and_reset_daily_count()`
   - NEW words contribute to daily count

3. **State Transitions**:
   - NEW → LEARNING (counts toward daily limit)
   - LEARNING → KNOWN (no limit impact)

## 🔒 Security & Validation

### Backend Validation

- **Pro Check**: `profile.can_modify_daily_new_word_target()`
- **Range Validation**: 5 ≤ target ≤ 100
- **Type Validation**: Integer values only
- **Authentication**: Token-based API access

### Frontend Protection

- **Disabled Input**: Free users see disabled field
- **Visual Indicators**: "Pro Only" badges and overlays
- **Upgrade Links**: Direct paths to subscription page
- **Client-side Validation**: Min/max attributes on inputs

## 🎯 Future Enhancements

- **Analytics**: Track usage patterns of different target values
- **Recommendations**: AI-powered target suggestions
- **Adaptive Targets**: Dynamic adjustment based on performance
- **Team Features**: Shared target goals for organizations
- **Gamification**: Streak tracking and achievement systems

## 📈 Metrics to Monitor

- **Engagement**: Pro vs. Free user review completion rates
- **Conversion**: Free users upgrading after hitting limits
- **Performance**: Impact of different targets on retention
- **Usage**: Most popular target values among Pro users

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: June 23, 2025 