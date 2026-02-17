from rest_framework import serializers
from .models import Report, ReportSchedule
from apps.users.serializers import UserShortSerializer


class ReportSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отчета.
    """
    report_type_display = serializers.CharField(
        source='get_report_type_display', 
        read_only=True
    )
    format_display = serializers.CharField(
        source='get_format_display', 
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    created_by = UserShortSerializer(read_only=True)
    processing_time = serializers.FloatField(read_only=True)
    filename = serializers.CharField(read_only=True)
    is_ready = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id',
            'report_number',
            'report_type',
            'report_type_display',
            'format',
            'format_display',
            'status',
            'status_display',
            'parameters',
            'file',
            'file_size',
            'error_message',
            'created_by',
            'created_at',
            'started_at',
            'completed_at',
            'processing_time',
            'filename',
            'is_ready',
        ]
        read_only_fields = [
            'id', 'report_number', 'file', 'file_size',
            'error_message', 'created_at', 'started_at', 'completed_at'
        ]


class ReportDetailSerializer(ReportSerializer):
    """
    Детальный сериализатор отчета.
    """
    class Meta(ReportSerializer.Meta):
        pass


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания отчета.
    """
    class Meta:
        model = Report
        fields = [
            'report_type',
            'format',
            'parameters',
        ]
    
    def validate_parameters(self, value):
        """Валидация параметров отчета"""
        report_type = self.initial_data.get('report_type')
        
        if not isinstance(value, dict):
            raise serializers.ValidationError('Параметры должны быть объектом JSON')
        
        # Базовая валидация в зависимости от типа отчета
        if 'orders' in report_type:
            if 'date_from' in value and 'date_to' in value:
                if value['date_from'] > value['date_to']:
                    raise serializers.ValidationError(
                        'Дата начала не может быть позже даты окончания'
                    )
        
        return value


class ReportScheduleSerializer(serializers.ModelSerializer):
    """
    Сериализатор для расписания отчетов.
    """
    report_type_display = serializers.CharField(
        source='get_report_type_display', 
        read_only=True
    )
    format_display = serializers.CharField(
        source='get_format_display', 
        read_only=True
    )
    frequency_display = serializers.CharField(
        source='get_frequency_display', 
        read_only=True
    )
    created_by = UserShortSerializer(read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id',
            'name',
            'report_type',
            'report_type_display',
            'format',
            'format_display',
            'frequency',
            'frequency_display',
            'parameters',
            'recipients',
            'is_active',
            'last_run',
            'next_run',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_run', 'next_run', 'created_at', 'updated_at']


class ReportScheduleCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания расписания.
    """
    class Meta:
        model = ReportSchedule
        fields = [
            'name',
            'report_type',
            'format',
            'frequency',
            'parameters',
            'recipients',
            'is_active',
        ]
    
    def validate_recipients(self, value):
        """Валидация email получателей"""
        if not isinstance(value, list):
            raise serializers.ValidationError('Получатели должны быть списком')
        
        import re
        email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        
        for email in value:
            if not email_pattern.match(email):
                raise serializers.ValidationError(f'Некорректный email: {email}')
        
        return value


class ReportParameterSerializer(serializers.Serializer):
    """
    Сериализатор для параметров отчета.
    """
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    store_id = serializers.IntegerField(required=False, allow_null=True)
    supplier_id = serializers.IntegerField(required=False, allow_null=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_null=True)
    role = serializers.CharField(required=False, allow_null=True)
    threshold = serializers.IntegerField(required=False, default=10)
    group_by = serializers.ChoiceField(
        required=False,
        choices=['day', 'week', 'month', 'year'],
        default='day'
    )
