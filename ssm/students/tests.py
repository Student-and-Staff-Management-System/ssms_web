from django.test import TestCase, Client
from django.urls import reverse
from students.models import Student, ScholarshipApplication

class StudentScholarshipAcademicYearTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = Student.objects.create(
            roll_number="2341101999",
            student_name="Kavitha R",
            student_email="kavitha@test.edu",
            program_level="UG",
            current_semester=4
        )
        # Setup student session
        session = self.client.session
        session['student_roll_number'] = self.student.roll_number
        session.save()

    def test_student_apply_and_year_reset(self):
        # 1. Apply for 2026-2027
        response = self.client.post(reverse('apply_scholarship'), {
            'academic_year': '2026-2027',
            'scholarship_type': 'POSTMATRIC',
            'application_no': 'TN-2026-101',
            'annual_income': '120000',
            'bank_account_no': '9876543210',
            'bank_ifsc': 'SBIN0000123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        app_26 = ScholarshipApplication.objects.filter(student=self.student, academic_year='2026-2027').first()
        self.assertIsNotNone(app_26)
        self.assertEqual(app_26.academic_year, '2026-2027')
        self.assertEqual(app_26.scholarship_type, 'POSTMATRIC')

        # 2. Duplicate submission for same academic year should be blocked
        dup_response = self.client.post(reverse('apply_scholarship'), {
            'academic_year': '2026-2027',
            'scholarship_type': 'POSTMATRIC',
            'application_no': 'TN-2026-102'
        }, follow=True)
        self.assertEqual(dup_response.status_code, 200)
        # Count should still be 1 for 2026-2027
        self.assertEqual(ScholarshipApplication.objects.filter(student=self.student, academic_year='2026-2027').count(), 1)

        # 3. Change academic year to 2027-2028: eligibility resets, new application succeeds
        response_27 = self.client.post(reverse('apply_scholarship'), {
            'academic_year': '2027-2028',
            'scholarship_type': 'POSTMATRIC',
            'application_no': 'TN-2027-201',
            'annual_income': '130000',
            'bank_account_no': '9876543210',
            'bank_ifsc': 'SBIN0000123'
        }, follow=True)
        self.assertEqual(response_27.status_code, 200)

        app_27 = ScholarshipApplication.objects.filter(student=self.student, academic_year='2027-2028').first()
        self.assertIsNotNone(app_27)
        self.assertEqual(app_27.academic_year, '2027-2028')
        self.assertEqual(app_27.scholarship_type, 'POSTMATRIC')

        # 4. Filter view by previous academic year 2026-2027
        resp_view_26 = self.client.get(reverse('apply_scholarship') + '?academic_year=2026-2027')
        self.assertEqual(resp_view_26.status_code, 200)
        apps_view_26 = list(resp_view_26.context['applications'])
        self.assertIn(app_26, apps_view_26)
        self.assertNotIn(app_27, apps_view_26)

        # 5. Filter view by new academic year 2027-2028
        resp_view_27 = self.client.get(reverse('apply_scholarship') + '?academic_year=2027-2028')
        self.assertEqual(resp_view_27.status_code, 200)
        apps_view_27 = list(resp_view_27.context['applications'])
        self.assertIn(app_27, apps_view_27)
        self.assertNotIn(app_26, apps_view_27)

        # 6. All years view shows both
        resp_view_all = self.client.get(reverse('apply_scholarship') + '?academic_year=all')
        self.assertEqual(resp_view_all.status_code, 200)
        apps_view_all = list(resp_view_all.context['applications'])
        self.assertIn(app_26, apps_view_all)
        self.assertIn(app_27, apps_view_all)
