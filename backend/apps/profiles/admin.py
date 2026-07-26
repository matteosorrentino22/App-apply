from django.contrib import admin

from .models import Certification, Education, Experience, Language, Profile, Skill


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 0


class LanguageInline(admin.TabularInline):
    model = Language
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "summary")
    inlines = [ExperienceInline, EducationInline, SkillInline, CertificationInline, LanguageInline]
