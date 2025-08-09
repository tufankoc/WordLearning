# Kelime Admin Features & User Analytics

This document outlines the comprehensive admin features implemented for the Kelime vocabulary learning platform. These features provide detailed insights into user behavior, engagement patterns, and system health for internal monitoring and decision-making.

## 🎯 Overview

The admin system has been enhanced with:
- **Detailed per-user statistics** in Django Admin
- **Advanced filtering and search capabilities**
- **Custom admin dashboard** with visualizations
- **CSV export functionality**
- **Management command for automated reports**

## 📊 Enhanced Django Admin

### Custom User Admin (`/admin/auth/user/`)

The default Django User admin has been completely customized to show:

#### List View Columns:
- **Username** & **Email** - Basic user identification
- **Pro Status** - Color-coded Pro/Free status with expiry dates
- **Date Joined** & **Last Login** - Account timeline
- **Sources** - Total sources with links to user's sources (shows limit for free users)
- **Known Words** - Known/Total words with percentage and links to user's words
- **Total Reviews** - Total and recent (7-day) review counts
- **Last Activity** - Most recent activity across all user actions
- **Learning Streak** - Current consecutive learning days

#### Advanced Filters:
- **User Activity Level**: Active Today/Week/Month, Inactive >1 Week/Month, Never Logged In
- **Word Count Range**: No Words, Beginner (1-10), Learning (11-50), Intermediate (51-100), Advanced (101-500), Power User (500+)
- **Source Count**: No Sources, 1-2 Sources, At Free Limit (3), Pro User (4+)
- **Pro Status**, **Activity Dates**, **Staff Status**

#### Admin Actions:
- **Make Pro** (unlimited)
- **Make Free**
- **Extend Pro** (1 year)
- **Export User Statistics** (CSV with comprehensive data)

### Other Enhanced Admin Models:

#### Source Admin:
- Shows user, word count, processing status
- Filters by source type, processing status, Pro/Free users
- Links to user's other sources

#### Word Admin:
- Total frequency across sources
- Number of users learning each word
- Definition preview

#### UserWordKnowledge Admin:
- Learning state, difficulty, review statistics
- Filters by learning state and Pro status

## 🚀 Admin Dashboard (`/admin-dashboard/`)

A comprehensive analytics dashboard accessible only to superusers:

### Key Metrics Cards:
- **Total Users** with new users this month
- **Pro Users** with conversion rate percentage
- **Active Users (30d)** with churn risk count
- **Words Learned Today** with total system words

### Interactive Charts:
- **Daily Active Users** (30-day line chart)
- **Sources Added Per Day** (30-day bar chart)
- **User Distribution** (Pro vs Free doughnut chart)

### Analytics Tables:
- **Engagement Metrics by User Type** - Average sources, words, and known words
- **Top 10 Most Active Users This Week** - Activity breakdown
- **Recent Activities Feed** - New registrations and Pro upgrades

### System Health Alerts:
- Free users at source limit (conversion opportunities)
- Power users with 100+ words (engagement opportunities)

## 📋 Management Command: `generate_user_report`

A powerful Django management command for generating detailed user analytics:

### Usage:
```bash
# Console report (default)
python manage.py generate_user_report --days 30

# CSV export
python manage.py generate_user_report --format csv --output user_report.csv

# Filter by user type
python manage.py generate_user_report --user-type pro --days 7
python manage.py generate_user_report --user-type inactive --days 30
```

### Options:
- `--format`: console, csv, json
- `--output`: Custom file path for exports
- `--days`: Analysis period (default: 30)
- `--user-type`: all, pro, free, active, inactive

### Report Contents:
- **Summary Statistics**: Total users, Pro conversion, activity metrics
- **Detailed User Data**: All user metrics in tabular format
- **Engagement Analysis**: Activity patterns and risk assessment
- **Export Capabilities**: CSV with comprehensive user statistics

## 🔧 Implementation Details

### Models Extended:
- **UserProfile**: Enhanced with Pro status tracking and activity dates
- **User**: Extended via custom admin with calculated fields
- **Source/Word/UserWordKnowledge**: Optimized queries and admin interfaces

### Performance Optimizations:
- **Prefetch Related**: Optimized querysets to avoid N+1 queries
- **Database Indexing**: Proper indexes on frequently queried fields
- **Selective Loading**: Only load necessary data for calculations

### Security Features:
- **Superuser Only**: Admin dashboard restricted to superusers
- **Staff Member Required**: Management commands require staff permissions
- **403 Error Page**: Custom error page for unauthorized access

## 📈 Business Intelligence Features

### User Segmentation:
- **Power Users**: 100+ words, high engagement
- **At-Risk Users**: Inactive >30 days
- **Conversion Candidates**: Free users at source limit
- **New Users**: Recent registrations requiring onboarding

### Engagement Metrics:
- **Learning Streaks**: Consecutive learning days
- **Review Patterns**: Daily/weekly review counts
- **Source Utilization**: Sources per user type
- **Knowledge Progression**: Known vs learning words ratio

### Conversion Tracking:
- **Pro Upgrade Patterns**: When users upgrade
- **Feature Usage**: Which features drive upgrades
- **Churn Risk**: Users likely to stop using the platform

## 🔗 Quick Access Links

- **Django Admin**: `/admin/`
- **Admin Dashboard**: `/admin-dashboard/`
- **User Management**: `/admin/auth/user/`
- **Source Analytics**: `/admin/core/source/`
- **Word Statistics**: `/admin/core/word/`

## 📊 Sample Reports

### Console Report Output:
```
================================================================================
USER ACTIVITY REPORT
================================================================================

Report Date: 2025-06-23
Analysis Period: 30 days
User Filter: all

TOTAL USERS: 150
Pro Users: 25 (16.7%)
Free Users: 125
Active (7d): 45
High Risk: 30

TOP 20 MOST ACTIVE USERS
--------------------------------------------------------------------------------
 1. user123         | Pro Active | Sources:  8 | Words: 245 | Score:  92 | Risk: Low      | Last: 0d
 2. learner456      | Free       | Sources:  3 | Words: 156 | Score:  78 | Risk: Low      | Last: 1d
```

### CSV Export Columns:
- Username, Email, Pro Status, Date Joined, Last Login
- Total Sources, Total Words, Known Words, Learning Words
- Total Reviews, Recent Reviews, Last Activity
- Daily Target, Words Today, Retention Rate

This comprehensive admin system provides your team with deep insights into user behavior, enabling data-driven decisions for product improvements, user engagement strategies, and business growth. 