from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg, Max, Sum
from django.utils import timezone
from datetime import timedelta
import csv
import os
from core.models import UserWordKnowledge, Source, UserProfile


class Command(BaseCommand):
    help = "Generate detailed user activity and engagement reports"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            type=str,
            choices=["csv", "json", "console"],
            default="console",
            help="Output format for the report"
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (for csv/json formats)"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to analyze (default: 30)"
        )
        parser.add_argument(
            "--user-type",
            type=str,
            choices=["all", "pro", "free", "active", "inactive"],
            default="all",
            help="Filter users by type"
        )

    def handle(self, *args, **options):
        days = options["days"]
        user_type = options["user_type"]
        output_format = options["format"]
        output_file = options["output"]

        # Calculate date ranges
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        week_ago = end_date - timedelta(days=7)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generating user activity report for the last {days} days..."
            )
        )

        # Build base queryset
        queryset = User.objects.select_related("profile").prefetch_related(
            "sources", "word_knowledge"
        )

        # Filter by user type
        if user_type == "pro":
            queryset = queryset.filter(profile__is_pro=True)
        elif user_type == "free":
            queryset = queryset.filter(
                Q(profile__is_pro=False) | Q(profile__isnull=True)
            )
        elif user_type == "active":
            queryset = queryset.filter(
                Q(last_login__gte=week_ago) |
                Q(profile__last_learning_date__gte=week_ago)
            ).distinct()
        elif user_type == "inactive":
            queryset = queryset.filter(
                Q(last_login__lt=week_ago) | Q(last_login__isnull=True)
            ).exclude(
                profile__last_learning_date__gte=week_ago
            ).distinct()

        # Annotate with statistics
        users_with_stats = queryset.annotate(
            total_sources=Count("sources"),
            total_words=Count("word_knowledge"),
            known_words=Count("word_knowledge", filter=Q(word_knowledge__state="KNOWN")),
            learning_words=Count("word_knowledge", filter=Q(word_knowledge__state="LEARNING")),
            total_reviews=Sum("word_knowledge__successful_reviews"),
            last_source_date=Max("sources__created_at"),
            last_word_review=Max("word_knowledge__last_review")
        )

        # Generate report data
        report_data = []
        for user in users_with_stats:
            profile = getattr(user, "profile", None)
            
            # Calculate last activity
            activities = []
            if user.last_login:
                activities.append(user.last_login)
            if profile and profile.last_learning_date:
                learning_datetime = timezone.make_aware(
                    timezone.datetime.combine(profile.last_learning_date, timezone.datetime.min.time())
                )
                activities.append(learning_datetime)
            if user.last_word_review:
                activities.append(user.last_word_review)
            if user.last_source_date:
                activities.append(user.last_source_date)
            
            last_activity = max(activities) if activities else None
            days_since_activity = (timezone.now() - last_activity).days if last_activity else None

            # Determine user status
            if profile and profile.is_pro_active():
                status = "Pro Active"
            elif profile and profile.is_pro:
                status = "Pro Expired"
            else:
                status = "Free"

            user_data = {
                "username": user.username,
                "email": user.email,
                "status": status,
                "date_joined": user.date_joined.strftime("%Y-%m-%d"),
                "last_login": user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never",
                "total_sources": user.total_sources,
                "total_words": user.total_words,
                "known_words": user.known_words or 0,
                "learning_words": user.learning_words or 0,
                "total_reviews": user.total_reviews or 0,
                "last_activity": last_activity.strftime("%Y-%m-%d %H:%M") if last_activity else "Never",
                "days_since_activity": days_since_activity,
                "daily_target": profile.daily_learning_target if profile else 0,
                "words_today": profile.words_learned_today if profile else 0,
            }
            report_data.append(user_data)

        # Sort by last activity
        report_data.sort(key=lambda x: x["days_since_activity"] if x["days_since_activity"] is not None else 999)

        # Generate summary statistics
        total_users = len(report_data)
        pro_users = len([u for u in report_data if u["status"].startswith("Pro")])
        active_users = len([u for u in report_data if u["days_since_activity"] is not None and u["days_since_activity"] <= 7])

        summary = {
            "report_date": end_date.strftime("%Y-%m-%d"),
            "analysis_period": f"{days} days",
            "user_filter": user_type,
            "total_users": total_users,
            "pro_users": pro_users,
            "free_users": total_users - pro_users,
            "active_users_7d": active_users,
        }

        # Output report
        if output_format == "console":
            self.display_console_report(summary, report_data[:20])  # Top 20 users
        elif output_format == "csv":
            self.export_csv_report(report_data, summary, output_file)

        self.stdout.write(
            self.style.SUCCESS(f"Report generated successfully for {total_users} users!")
        )

    def display_console_report(self, summary, top_users):
        """Display report in console format"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("USER ACTIVITY REPORT"))
        self.stdout.write(self.style.SUCCESS("="*80))
        
        # Summary
        self.stdout.write(f"\nReport Date: {summary['report_date']}")
        self.stdout.write(f"Analysis Period: {summary['analysis_period']}")
        self.stdout.write(f"User Filter: {summary['user_filter']}")
        self.stdout.write(f"\nTOTAL USERS: {summary['total_users']}")
        self.stdout.write(f"Pro Users: {summary['pro_users']}")
        self.stdout.write(f"Free Users: {summary['free_users']}")
        self.stdout.write(f"Active (7d): {summary['active_users_7d']}")

        # Top users
        self.stdout.write(self.style.WARNING("\n" + "-"*80))
        self.stdout.write(self.style.WARNING("TOP 20 MOST ACTIVE USERS"))
        self.stdout.write(self.style.WARNING("-"*80))
        
        for i, user in enumerate(top_users[:20], 1):
            days_str = str(user["days_since_activity"]) + "d" if user["days_since_activity"] else "Never"
            self.stdout.write(f"{i:2d}. {user['username']:<15} | {user['status']:<10} | Sources: {user['total_sources']:2d} | Words: {user['total_words']:3d} | Last: {days_str}")

    def export_csv_report(self, report_data, summary, output_file):
        """Export report to CSV format"""
        if not output_file:
            output_file = f"user_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = list(report_data[0].keys()) if report_data else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(report_data)
        
        self.stdout.write(f"CSV report exported to: {output_file}")
