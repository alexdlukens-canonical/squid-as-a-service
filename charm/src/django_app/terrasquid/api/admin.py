from django.contrib import admin

from .models import ACLRule, ConfigVersion, DestinationConfig, DestinationGroup, PortGroup, SourceACL, SourceGroup

admin.site.register(SourceACL)
admin.site.register(SourceGroup)
admin.site.register(PortGroup)
admin.site.register(DestinationConfig)
admin.site.register(DestinationGroup)
admin.site.register(ACLRule)
admin.site.register(ConfigVersion)
