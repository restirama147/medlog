from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from assets.models import Asset, Category
from maintenance.models import MaintenanceRecord, SparePartReplacement
import json

class AssetBackendTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teknisi_test',
            password='Password123!',
            role='engineer',
            first_name='Rega',
            last_name='Teknisi'
        )
        self.client = Client()
        self.client.login(username='teknisi_test', password='Password123!')

        self.category = Category.objects.create(name='Peralatan Life Support')
        self.asset = Asset.objects.create(
            code='AST-TEST-001',
            name='Syringe Pump',
            brand='Terumo',
            model_type='TE-SS700',
            serial_number='SN-998877',
            category=self.category,
            location='Ruang ICU',
            installation_year=2023,
            status='active',
            calibration_status='active',
            spo_text='Langkah 1: Periksa kabel daya.'
        )

    def test_asset_properties(self):
        self.assertEqual(self.asset.full_brand, 'Terumo TE-SS700')
        self.assertEqual(self.asset.status_label, 'Layak Pakai')
        self.assertEqual(self.asset.status_css, 'success')
        self.assertEqual(self.asset.calib_label, 'Aktif')

    def test_asset_index_view(self):
        response = self.client.get(reverse('assets:view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Syringe Pump')
        self.assertContains(response, 'AST-TEST-001')

    def test_create_asset_api(self):
        payload = {
            'code': 'AST-NEW-002',
            'name': 'Patient Monitor',
            'brand': 'Mindray uMEC 10',
            'sn': 'MN-112233',
            'location': 'Kamar Bedah (OK)',
            'year': 2024,
            'status': 'Layak Pakai',
            'calibration_status': 'Aktif'
        }
        response = self.client.post(
            reverse('assets:create'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Asset.objects.filter(code='AST-NEW-002').exists())

    def test_api_asset_detail(self):
        response = self.client.get(reverse('assets:api_detail', kwargs={'pk': self.asset.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 'AST-TEST-001')
        self.assertEqual(data['name'], 'Syringe Pump')

    def test_save_corrective_action(self):
        payload = {
            'asset_id': self.asset.id,
            'code': self.asset.code,
            'wo_no': 'CM-ICU-TEST01',
            'tgl_lapor': '2026-11-11',
            'pelapor': 'Ns. Siti',
            'urgency': 'high',
            'deskripsi': 'Sensor macet',
            'root_cause': 'Sensor aus',
            'tindakan': 'Penggantian sensor',
            'status_akhir': 'Layak Pakai',
            'spareparts': [
                {'name': 'Sensor Infus', 'qty': 1, 'sn': 'PART-01'}
            ]
        }
        response = self.client.post(
            reverse('assets:save_corrective'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(MaintenanceRecord.objects.filter(work_order_no='CM-ICU-TEST01').exists())
        self.assertTrue(SparePartReplacement.objects.filter(part_name='Sensor Infus').exists())
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'active')

    def test_public_asset_info_view(self):
        # Tambah record maintenance preventif & perbaikan untuk tes
        MaintenanceRecord.objects.create(
            work_order_no='WO-PREV-001',
            maintenance_type='preventive',
            asset=self.asset,
            date='2026-11-15',
            result_status='Layak Pakai',
            notes='Check berkala OK'
        )
        corr = MaintenanceRecord.objects.create(
            work_order_no='CM-TEST-999',
            maintenance_type='corrective',
            asset=self.asset,
            date='2026-11-16',
            reporter_name='Ruang Bedah',
            urgency='high',
            damage_description='Baterai drop',
            root_cause='Baterai aus',
            action_taken='Ganti baterai baru',
            result_status='Layak Pakai'
        )
        SparePartReplacement.objects.create(
            maintenance_record=corr,
            part_name='Baterai Li-Ion 12V',
            quantity=1,
            serial_number='BAT-123'
        )

        # Public URL dapat diakses tanpa login
        anon_client = Client()
        response = anon_client.get(reverse('assets:public_info', kwargs={'pk': self.asset.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Syringe Pump')
        self.assertContains(response, 'SN-998877')
        self.assertContains(response, 'Terumo TE-SS700')
        # Cek apakah riwayat maintenance & korektif tampil
        self.assertContains(response, 'WO-PREV-001')
        self.assertContains(response, 'CM-TEST-999')
        self.assertContains(response, 'Baterai Li-Ion 12V')
        self.assertContains(response, 'Riwayat Maintenance Preventif Rutin')
        self.assertContains(response, 'Riwayat Tindakan Perbaikan / Korektif')

    def test_print_qr_labels_view(self):
        response = self.client.get(reverse('assets:print_labels') + f'?ids={self.asset.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Syringe Pump')
        self.assertContains(response, 'SN-998877')
        self.assertContains(response, 'data:image/png;base64')

