from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from staffs.models import Staff, AdminSettings, Lab

class AdminSettingsTestCase(TestCase):
    def setUp(self):
        AdminSettings.objects.all().delete()
        Staff.objects.all().delete()

    def test_singleton_admin_settings(self):
        settings1 = AdminSettings.objects.create(max_additional_admins=3)
        self.assertEqual(AdminSettings.objects.count(), 1)

        # Attempt to create another one should fail clean validation
        settings2 = AdminSettings(max_additional_admins=5)
        with self.assertRaises(ValidationError):
            settings2.clean()

    def test_staff_admin_limit(self):
        AdminSettings.objects.create(max_additional_admins=2)

        staff1 = Staff.objects.create(
            staff_id="TEST01",
            name="Admin One",
            email="admin1@example.com",
            is_admin=True,
            is_active=True
        )
        staff1.clean()

        staff2 = Staff.objects.create(
            staff_id="TEST02",
            name="Admin Two",
            email="admin2@example.com",
            is_admin=True,
            is_active=True
        )
        staff2.clean()

        staff3 = Staff(
            staff_id="TEST03",
            name="Admin Three",
            email="admin3@example.com",
            is_admin=True,
            is_active=True
        )
        with self.assertRaises(ValidationError):
            staff3.clean()

        staff3.is_admin = False
        staff3.save()
        staff3.clean()

    def test_change_limit_validation(self):
        settings = AdminSettings.objects.create(max_additional_admins=2)

        Staff.objects.create(staff_id="TEST01", name="A1", email="a1@example.com", is_admin=True)
        Staff.objects.create(staff_id="TEST02", name="A2", email="a2@example.com", is_admin=True)

        settings.max_additional_admins = 1
        with self.assertRaises(ValidationError):
            settings.clean()

        settings.max_additional_admins = 3
        settings.clean()


class LabManagementTestCase(TestCase):
    def setUp(self):
        Lab.objects.all().delete()
        Staff.objects.all().delete()
        
        # Create HOD
        self.hod = Staff.objects.create(
            staff_id="HOD01",
            name="HOD User",
            email="hod@example.com",
            role="HOD",
            is_active=True
        )
        self.hod.set_password("password123")
        self.hod.save()

        # Create Class Incharge
        self.staff_member = Staff.objects.create(
            staff_id="STAFF01",
            name="Staff User",
            email="staff@example.com",
            role="Class Incharge",
            is_active=True
        )
        self.staff_member.set_password("password123")
        self.staff_member.save()

    def test_lab_creation_and_assignment(self):
        lab = Lab.objects.create(
            name="Web Tech Lab",
            short_name="IT-LAB-05",
            staff=self.staff_member
        )
        self.assertEqual(lab.name, "Web Tech Lab")
        self.assertEqual(lab.short_name, "IT-LAB-05")
        self.assertEqual(lab.staff, self.staff_member)
        self.assertIn(lab, self.staff_member.assigned_labs.all())

    def test_hod_manage_labs_view_access(self):
        # Non-logged in users should redirect to login
        response = self.client.get(reverse('staffs:hod_manage_labs'))
        self.assertRedirects(response, reverse('staffs:stafflogin'))

        # Class Incharge should be blocked and redirected with error
        session = self.client.session
        session['staff_id'] = self.staff_member.staff_id
        session.save()
        
        response = self.client.get(reverse('staffs:hod_manage_labs'))
        self.assertRedirects(response, reverse('staffs:staff_dashboard'))

        # HOD should be able to access
        session['staff_id'] = self.hod.staff_id
        session.save()
        response = self.client.get(reverse('staffs:hod_manage_labs'))
        self.assertEqual(response.status_code, 200)

    def test_hod_create_edit_delete_lab(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # 1. Create Lab via POST
        post_data = {
            'action': 'create',
            'name': 'New OS Lab',
            'short_name': 'OS-LAB-10',
            'staff_id': self.staff_member.staff_id
        }
        response = self.client.post(reverse('staffs:hod_manage_labs'), post_data)
        self.assertRedirects(response, reverse('staffs:hod_manage_labs'))
        self.assertTrue(Lab.objects.filter(short_name='OS-LAB-10').exists())
        lab = Lab.objects.get(short_name='OS-LAB-10')
        self.assertEqual(lab.name, 'New OS Lab')
        self.assertEqual(lab.staff, self.staff_member)

        # 2. Edit Lab via POST
        edit_data = {
            'action': 'edit',
            'lab_id': lab.id,
            'name': 'Updated OS Lab',
            'short_name': 'OS-LAB-11',
            'staff_id': '' # Unassign
        }
        response = self.client.post(reverse('staffs:hod_manage_labs'), edit_data)
        self.assertRedirects(response, reverse('staffs:hod_manage_labs'))
        lab.refresh_from_db()
        self.assertEqual(lab.name, 'Updated OS Lab')
        self.assertEqual(lab.short_name, 'OS-LAB-11')
        self.assertIsNone(lab.staff)

        # 3. Delete Lab via GET delete route
        response = self.client.get(reverse('staffs:hod_delete_lab', args=[lab.id]))
        self.assertRedirects(response, reverse('staffs:hod_manage_labs'))
        self.assertFalse(Lab.objects.filter(id=lab.id).exists())

    def test_dashboard_context_reflection(self):
        # Assign a lab to staff
        Lab.objects.create(name="Networks Lab", short_name="NW-LAB", staff=self.staff_member)

        # Log in as Class Incharge and hit dashboard
        session = self.client.session
        session['staff_id'] = self.staff_member.staff_id
        session.save()

        response = self.client.get(reverse('staffs:staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('assigned_labs', response.context)
        self.assertEqual(response.context['assigned_labs'].count(), 1)
        self.assertEqual(response.context['assigned_labs'].first().short_name, "NW-LAB")


class BatchAndRepresentativeTestCase(TestCase):
    def setUp(self):
        from students.models import Student
        from staffs.models import Staff, Subject, Timetable
        Student.objects.all().delete()
        Staff.objects.all().delete()
        Subject.objects.all().delete()
        Timetable.objects.all().delete()

        # Create HOD
        self.hod = Staff.objects.create(
            staff_id="HOD01",
            name="HOD User",
            email="hod@example.com",
            role="HOD",
            is_active=True
        )
        self.hod.set_password("password123")
        self.hod.save()

        # Create Students in Semester 5
        self.student1 = Student.objects.create(
            roll_number="STUD01",
            student_name="Student One",
            student_email="stud1@example.com",
            current_semester=5,
            is_profile_complete=True
        )
        self.student2 = Student.objects.create(
            roll_number="STUD02",
            student_name="Student Two",
            student_email="stud2@example.com",
            current_semester=5,
            is_profile_complete=True
        )
        self.student3 = Student.objects.create(
            roll_number="STUD03",
            student_name="Student Three",
            student_email="stud3@example.com",
            current_semester=5,
            is_profile_complete=True
        )
        self.phd_student = Student.objects.create(
            roll_number="PHDSTUD01",
            student_name="PhD Student",
            student_email="phd@example.com",
            current_semester=5,
            program_level="PHD",
            is_profile_complete=True
        )

        # Create Subject for Semester 5
        self.subject = Subject.objects.create(
            code="CS8501",
            name="Theory of Computation",
            semester=5,
            credits=4,
            subject_type="Theory",
            staff=self.hod
        )

    def test_assign_batches_and_representatives(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # Test GET request context list segregation
        get_response = self.client.get(reverse('staffs:assign_lab_batches') + '?semester=5')
        self.assertIn('batch_a_students', get_response.context)
        self.assertIn('batch_b_students', get_response.context)
        self.assertIn('unassigned_students', get_response.context)
        self.assertNotIn(self.phd_student, get_response.context['batch_a_students'])
        self.assertNotIn(self.phd_student, get_response.context['batch_b_students'])
        self.assertNotIn(self.phd_student, get_response.context['unassigned_students'])
        self.assertNotIn(self.phd_student, get_response.context['students'])

        # 1. Assign to Batch A & B, make stud1 and stud2 reps
        post_data = {
            'semester': '5',
            f'batch_{self.student1.roll_number}': 'A',
            f'rep_{self.student1.roll_number}': 'true',
            f'batch_{self.student2.roll_number}': 'A',
            f'rep_{self.student2.roll_number}': 'true',
            f'batch_{self.student3.roll_number}': 'B',
        }
        response = self.client.post(reverse('staffs:assign_lab_batches'), post_data)
        self.assertRedirects(response, '/staffs/assign-batches/?semester=5')

        self.student1.refresh_from_db()
        self.student2.refresh_from_db()
        self.student3.refresh_from_db()

        self.assertEqual(self.student1.lab_batch, 'A')
        self.assertTrue(self.student1.is_class_representative)
        self.assertEqual(self.student2.lab_batch, 'A')
        self.assertTrue(self.student2.is_class_representative)
        self.assertEqual(self.student3.lab_batch, 'B')
        self.assertFalse(self.student3.is_class_representative)

    def test_assign_representatives_validation_over_limit(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # Try to assign 3 reps to Batch A
        post_data = {
            'semester': '5',
            f'batch_{self.student1.roll_number}': 'A',
            f'rep_{self.student1.roll_number}': 'true',
            f'batch_{self.student2.roll_number}': 'A',
            f'rep_{self.student2.roll_number}': 'true',
            f'batch_{self.student3.roll_number}': 'A',
            f'rep_{self.student3.roll_number}': 'true',
        }
        response = self.client.post(reverse('staffs:assign_lab_batches'), post_data)
        self.assertRedirects(response, '/staffs/assign-batches/?semester=5')
        
        # Verify changes were NOT applied
        self.student1.refresh_from_db()
        self.assertFalse(self.student1.is_class_representative)

    def test_assign_representatives_validation_no_batch(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # Try to make student a representative without a batch
        post_data = {
            'semester': '5',
            f'batch_{self.student1.roll_number}': '',
            f'rep_{self.student1.roll_number}': 'true',
        }
        response = self.client.post(reverse('staffs:assign_lab_batches'), post_data)
        self.assertRedirects(response, '/staffs/assign-batches/?semester=5')
        
        self.student1.refresh_from_db()
        self.assertFalse(self.student1.is_class_representative)

    def test_timetable_batch_filtering_and_saving(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # 1. Edit Timetable in Combined Mode
        post_data = {
            'current_batch': 'All',
            f'subject_Monday_1': str(self.subject.id),
        }
        response = self.client.post(reverse('staffs:edit_timetable', args=[5]), post_data)
        self.assertRedirects(response, '/staffs/timetable/?semester=5')

        from staffs.models import Timetable
        self.assertTrue(Timetable.objects.filter(semester=5, day='Monday', period=1, batch='All').exists())

        # 2. Edit Timetable in Batch A mode to override Monday Period 1
        # Create a new subject for the override
        from staffs.models import Subject
        override_subject = Subject.objects.create(
            code="CS8502",
            name="Microprocessors",
            semester=5,
            credits=3,
            subject_type="Theory",
            staff=self.hod
        )
        post_override = {
            'current_batch': 'A',
            f'subject_Monday_1': str(override_subject.id),
        }
        response = self.client.post(reverse('staffs:edit_timetable', args=[5]), post_override)
        self.assertRedirects(response, '/staffs/timetable/?semester=5')

        # 'All' entry should be split/deleted, Batch A should have CS8502, Batch B should have original CS8501
        self.assertFalse(Timetable.objects.filter(semester=5, day='Monday', period=1, batch='All').exists())
        self.assertTrue(Timetable.objects.filter(semester=5, day='Monday', period=1, batch='A', subject=override_subject).exists())
        self.assertTrue(Timetable.objects.filter(semester=5, day='Monday', period=1, batch='B', subject=self.subject).exists())


class AdditionalRolesTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.hashers import make_password
        self.staff = Staff.objects.create(
            staff_id="STAFF_TEST_ROLE",
            name="Test Role Faculty",
            email="testrole@example.com",
            password=make_password("password123"),
            role="Course Incharge",
            is_profile_complete=True
        )
        self.hod = Staff.objects.create(
            staff_id="HOD_TEST_ROLE",
            name="HOD Role Faculty",
            email="hodrole@example.com",
            password=make_password("password123"),
            role="HOD",
            is_profile_complete=True
        )

    def test_timetable_incharge_role_access(self):
        # By default, a Course Incharge gets redirect on edit_timetable
        self.client.login(username=self.staff.staff_id, password="password123")
        session = self.client.session
        session['staff_id'] = self.staff.staff_id
        session.save()

        response = self.client.get(reverse('staffs:edit_timetable', args=[5]))
        self.assertRedirects(response, '/staffs/timetable/')

        response = self.client.get(reverse('staffs:assign_lab_batches') + '?semester=5')
        self.assertRedirects(response, '/staffs/dashboard/')

        # Elevate to timetable incharge
        self.staff.is_timetable_incharge = True
        self.staff.save()

        response = self.client.get(reverse('staffs:edit_timetable', args=[5]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('staffs:assign_lab_batches') + '?semester=5')
        self.assertEqual(response.status_code, 200)

    def test_scholarship_officer_role_access(self):
        # By default, Course Incharge gets redirect on scholarship_manager
        self.client.login(username=self.staff.staff_id, password="password123")
        session = self.client.session
        session['staff_id'] = self.staff.staff_id
        session.save()

        response = self.client.get(reverse('staffs:scholarship_manager'))
        self.assertRedirects(response, '/staffs/dashboard/')

        # Elevate to scholarship officer
        self.staff.is_scholarship_officer = True
        self.staff.save()

        response = self.client.get(reverse('staffs:scholarship_manager'))
        self.assertEqual(response.status_code, 200)

    def test_timetable_incharge_and_scholarship_officer_limits(self):
        # Create a second timetable incharge and a second scholarship officer (fine, count=2)
        staff2 = Staff.objects.create(
            staff_id="STAFF2",
            name="Staff Two",
            email="staff2@example.com",
            is_timetable_incharge=True,
            is_scholarship_officer=True,
            is_profile_complete=True
        )

        # Update self.staff to be timetable incharge and scholarship officer as well (fine, count=2)
        self.staff.is_timetable_incharge = True
        self.staff.is_scholarship_officer = True
        self.staff.save()

        # Attempt to create a third timetable incharge should fail validation
        staff3 = Staff(
            staff_id="STAFF3",
            name="Staff Three",
            email="staff3@example.com",
            is_timetable_incharge=True,
            is_profile_complete=True
        )
        with self.assertRaises(ValidationError):
            staff3.clean()

        # Attempt to create a third scholarship officer should fail validation
        staff4 = Staff(
            staff_id="STAFF4",
            name="Staff Four",
            email="staff4@example.com",
            is_scholarship_officer=True,
            is_profile_complete=True
        )
        with self.assertRaises(ValidationError):
            staff4.clean()




