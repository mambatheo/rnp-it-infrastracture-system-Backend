from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Region, DPU, Station


class BaseRegionFilter(admin.SimpleListFilter):
    """Base filter for Region - works for all equipment models"""
    title = _('Region')
    parameter_name = 'region'

    def lookups(self, request, model_admin):
        """Return all regions"""
        regions = Region.objects.all().order_by('name')
        return [(region.id, region.name) for region in regions]

    def queryset(self, request, queryset):
        """Filter by selected region"""
        if self.value():
            return queryset.filter(region_id=self.value())
        return queryset


class BaseDPUFilter(admin.SimpleListFilter):
    """Base filter for DPU - works for all equipment models"""
    title = _('DPU')
    parameter_name = 'dpu'

    def lookups(self, request, model_admin):
        """Return DPUs filtered by selected region"""
        region_id = request.GET.get('region')
        
        if region_id:
         
            dpus = DPU.objects.filter(region_id=region_id).order_by('name')
            return [(dpu.id, dpu.name) for dpu in dpus]
        else:
        
            dpus = DPU.objects.select_related('region').order_by('region__name', 'name')
            return [(dpu.id, f"{dpu.name} ({dpu.region.name})") for dpu in dpus]

    def queryset(self, request, queryset):
        """Filter by selected DPU"""
        if self.value():
            return queryset.filter(dpu_id=self.value())
        return queryset


class BaseStationFilter(admin.SimpleListFilter):
    """Base filter for Station - works for all equipment models"""
    title = _('Station')
    parameter_name = 'station'

    def lookups(self, request, model_admin):
        """Return stations filtered by selected DPU or Region"""
        dpu_id = request.GET.get('dpu')
        region_id = request.GET.get('region')
        
        if dpu_id:
            
            stations = Station.objects.filter(dpu_id=dpu_id).order_by('name')
            return [(station.id, station.name) for station in stations]
        elif region_id:
          
            stations = Station.objects.filter(
                dpu__region_id=region_id
            ).select_related('dpu').order_by('dpu__name', 'name')
            return [(station.id, f"{station.name} ({station.dpu.name})") for station in stations]
        else:
          
            stations = Station.objects.select_related(
                'dpu', 'dpu__region'
            ).order_by('dpu__region__name', 'dpu__name', 'name')
            return [(station.id, f"{station.name} - {station.dpu.name}") for station in stations]

    def queryset(self, request, queryset):
        """Filter by selected station"""
        if self.value():
            return queryset.filter(station_id=self.value())
        return queryset


# Aliases for backward compatibility
RegionFilter = BaseRegionFilter
DPUFilter = BaseDPUFilter
StationFilter = BaseStationFilter