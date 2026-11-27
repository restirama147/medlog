from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from assets.models import Asset, Category
from maintenance.models import MaintenanceRecord
import json

class MaintenanceBackendTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='engineer_medik',
            password='Password123!',
            role='engineer',
            first_name='Ahmad',
            last_name='Teknisi'
        )
        self.client = Client()
        self.client.login(username='engineer_medik', password='Password123!')

        self.category = Category.objects.create(
            name='Ventilator',
            slug='ventilator',
            accessories_template=['Patient Circuit', 'O2 Sensor'],
            inspection_template=['Chasis / Selungkup', 'Kabel Catu Daya']
        )

        self.asset = Asset.objects.create(
            code='AST-VENT-01',
            name='Ventilator',
            brand='Carefusion',
            model_type='LVT-1200',
            serial_number='VENT-SN-01',
            location='Ruang ICU',
            installation_year=2022,
            category=self.category,
            status='active'
        )

    def test_maintenance_index_view(self):
        response = self.client.get(reverse('maintenance:view') + f'?asset_id={self.asset.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ventilator')
        self.assertContains(response, 'Carefusion')

    def test_category_template_api(self):
        response = self.client.get(reverse('maintenance:category_template', kwargs={'category_id': self.category.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Ventilator')
        self.assertIn('Patient Circuit', data['accessories'])

    def test_save_preventive_maintenance(self):
        payload = {
            'asset_id': self.asset.id,
            'code': self.asset.code,
            'wo_no': 'WO-TEST-PREV01',
            'date': '2026-11-11',
            'start_time': '08:00',
            'end_time': '09:00',
            'result_status': 'Layak Pakai',
            'notes': 'Semua fungsi dalam kondisi optimal.',
            'accessories_check': {
                'Patient Circuit': 'Ada / Ya',
                'O2 Sensor': 'Ada / Ya'
            },
            'physical_check': {
                'Chasis / Selungkup': 'Baik',
                'Kabel Catu Daya': 'Baik'
            },
            'signature_user_name': 'Perawat ICU',
            'signature_engineer_name': 'Ahmad Teknisi'
        }
        response = self.client.post(
            reverse('maintenance:save_preventive'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(MaintenanceRecord.objects.filter(work_order_no='WO-TEST-PREV01').exists())

    def test_work_order_detail_view(self):
        record = MaintenanceRecord.objects.create(
            work_order_no='WO-TEST-PREV02',
            maintenance_type='preventive',
            asset=self.asset,
            date='2026-11-11',
            technician=self.user,
            technician_name='Ahmad Teknisi',
            result_status='Layak Pakai'
        )
        response = self.client.get(reverse('maintenance:detail', kwargs={'pk': record.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WO-TEST-PREV02')
        self.assertContains(response, 'Ventilator')
