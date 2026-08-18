from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from staffs.models import Staff, AdminSettings, Lab, ClassMapping, Subject, PublishedTimetableVersion, Timetable

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

    def test_hod_create_edit_delete_class_mapping(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # 1. Create Class Mapping via POST
        post_data = {
            'action': 'create_class',
            'class_name': 'III Year IT - Sem 5',
            'room_name': 'LH-201',
            'semester': '5'
        }
        response = self.client.post(reverse('staffs:hod_manage_labs'), post_data)
        self.assertRedirects(response, reverse('staffs:hod_manage_labs'))
        self.assertTrue(ClassMapping.objects.filter(room_name='LH-201').exists())
        cm = ClassMapping.objects.get(room_name='LH-201')
        self.assertEqual(cm.class_name, 'III Year IT - Sem 5')
        self.assertEqual(cm.semester, 5)

        # 2. Edit Class Mapping via POST
        edit_data = {
            'action': 'edit_class',
            'class_id': cm.id,
            'class_name': 'Updated III Year IT',
            'room_name': 'LH-202',
            'semester': '6'
        }
        response = self.client.post(reverse('staffs:hod_manage_labs'), edit_data)
        self.assertRedirects(response, reverse('staffs:hod_manage_labs'))
        cm.refresh_from_db()
        self.assertEqual(cm.class_name, 'Updated III Year IT')
        self.assertEqual(cm.room_name, 'LH-202')

        # 3. Delete Class Mapping via GET delete route
        response = self.client.get(reverse('staffs:hod_delete_class_mapping', args=[cm.id]))
        self.assertRedirects(response, reverse('staffs:hod_manage_labs'))
        self.assertFalse(ClassMapping.objects.filter(id=cm.id).exists())

    def test_subject_location_assignment_and_live_visualisation(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # 1. Create Subject with location_name via POST
        post_data = {
            'action': 'add_subject',
            'code': 'CS301',
            'name': 'Operating Systems',
            'semester': '5',
            'type': 'Theory',
            'location_name': 'LH-201'
        }
        response = self.client.post(reverse('staffs:manage_subjects'), post_data)
        self.assertRedirects(response, reverse('staffs:manage_subjects'))
        self.assertTrue(Subject.objects.filter(code='CS301').exists())
        subject = Subject.objects.get(code='CS301')
        self.assertEqual(subject.location_name, 'LH-201')
        self.assertEqual(subject.get_location_display(), 'LH-201')

        # 2. Test Live Class Visualisation View Access for HOD
        response = self.client.get(reverse('staffs:hod_live_class_visualisation'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('room_cards', response.context)

    def test_3hr_lab_merging_and_propagation(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # Create a Lab subject
        lab_subj = Subject.objects.create(
            code='CS302L',
            name='OS Laboratory',
            semester=5,
            subject_type='Lab',
            staff=self.hod
        )

        # Submit POST with Lab subject selected ONLY in Period 1
        post_data = {
            'academic_year': '2026-2027',
            'current_batch': 'All',
            'subject_Monday_1': str(lab_subj.id),
        }
        response = self.client.post(reverse('staffs:edit_timetable', args=[5]), post_data)
        self.assertRedirects(response, '/staffs/hod/published-timetables/?semester=5&academic_year=2026-2027&tab=edit')

        # Verify backend auto-propagated the 3-hour lab across Period 1, 2, and 3
        from staffs.models import Timetable
        p1_entry = Timetable.objects.filter(semester=5, day='Monday', period=1).first()
        p2_entry = Timetable.objects.filter(semester=5, day='Monday', period=2).first()
        p3_entry = Timetable.objects.filter(semester=5, day='Monday', period=3).first()

        self.assertIsNotNone(p1_entry)
        self.assertIsNotNone(p2_entry)
        self.assertIsNotNone(p3_entry)
        self.assertEqual(p1_entry.subject, lab_subj)
        self.assertEqual(p2_entry.subject, lab_subj)
        self.assertEqual(p3_entry.subject, lab_subj)

    def test_published_timetable_versioning_and_effect_dates(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # 1. Create a Timetable entry
        subj = Subject.objects.create(code='CS601', name='Algorithms', semester=6, subject_type='Theory')
        Timetable.objects.create(
            academic_year='2026-2027',
            semester=6,
            day='Monday',
            period=1,
            batch='All',
            subject=subj,
            staff=self.staff_member,
            is_published=True
        )

        # 2. Save Effect Dates via POST to hod_published_timetables
        post_data = {
            'action': 'set_effect_dates',
            'from_date': '2026-08-01',
            'to_date': '2026-12-31'
        }
        url = reverse('staffs:hod_published_timetables') + '?academic_year=2026-2027&semester=6'
        response = self.client.post(url, post_data)
        self.assertRedirects(response, url + '&tab=master')

        # Verify PublishedTimetableVersion created
        self.assertTrue(PublishedTimetableVersion.objects.filter(semester=6, academic_year='2026-2027').exists())
        ver = PublishedTimetableVersion.objects.get(semester=6, academic_year='2026-2027')
        self.assertEqual(str(ver.from_date), '2026-08-01')
        self.assertEqual(str(ver.to_date), '2026-12-31')
        self.assertTrue(ver.is_active)

        # 3. GET request: verify context contains previous_timetable_versions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('previous_timetable_versions', response.context)
        self.assertEqual(len(response.context['previous_timetable_versions']), 1)


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
        self.assertRedirects(response, '/staffs/hod/published-timetables/?semester=5&academic_year=2026-2027&tab=edit')

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
        self.assertRedirects(response, '/staffs/hod/published-timetables/?semester=5&academic_year=2026-2027&tab=edit')

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


class StaffPortfolioTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.hashers import make_password
        self.staff = Staff.objects.create(
            staff_id="PORTFOLIO_STAFF",
            name="Portfolio Faculty",
            email="portfaculty@example.com",
            password=make_password("password123"),
            role="Course Incharge",
            is_profile_complete=True
        )

    def test_portfolio_add_award(self):
        from staffs.models import StaffAwardHonour
        
        self.client.login(username=self.staff.staff_id, password="password123")
        session = self.client.session
        session['staff_id'] = self.staff.staff_id
        session.save()

        # Send POST request to add an award
        response = self.client.post(reverse('staffs:portfolio_add_award'), {
            'title': 'Best Teacher Award',
            'awarded_by': 'University',
            'description': 'Awarded for excellence in teaching.',
            'year': '2026',
            'category': 'Award',
        })
        
        # Verify redirect to staff_portfolio
        self.assertRedirects(response, reverse('staffs:staff_portfolio'))
        
        # Verify award was created and associated with staff
        awards = StaffAwardHonour.objects.filter(title='Best Teacher Award')
        self.assertEqual(awards.count(), 1)
        award = awards.first()
        self.assertIn(self.staff, award.staff.all())


class DepartmentTaskTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.hashers import make_password
        from staffs.models import DepartmentTask
        self.hod = Staff.objects.create(
            staff_id="HOD_TASK_TEST",
            name="HOD Task Admin",
            email="hodtaskadmin@example.com",
            password=make_password("password123"),
            role="HOD",
            is_profile_complete=True
        )
        self.faculty1 = Staff.objects.create(
            staff_id="FACULTY1_TASK",
            name="Faculty Member One",
            email="fac1task@example.com",
            password=make_password("password123"),
            role="Course Incharge",
            is_profile_complete=True
        )
        self.faculty2 = Staff.objects.create(
            staff_id="FACULTY2_TASK",
            name="Faculty Member Two",
            email="fac2task@example.com",
            password=make_password("password123"),
            role="Course Incharge",
            is_profile_complete=True
        )
        DepartmentTask.seed_default_tasks()

    def test_seed_tasks_count(self):
        from staffs.models import DepartmentTask
        self.assertEqual(DepartmentTask.objects.count(), 58)

    def test_manage_department_tasks_get_and_post(self):
        from staffs.models import DepartmentTask
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        # GET request
        response = self.client.get(reverse('staffs:manage_department_tasks'))
        self.assertEqual(response.status_code, 200)

        # Assign Task 1 (Department Administration) to both faculty members via checkboxes
        task1 = DepartmentTask.objects.get(task_number=1)
        post_data = {
            f'task_{task1.id}': [self.faculty1.staff_id, self.faculty2.staff_id]
        }
        post_response = self.client.post(reverse('staffs:manage_department_tasks'), post_data)
        self.assertRedirects(post_response, reverse('staffs:manage_department_tasks'))

        # Verify task 1 is assigned to both faculty members
        task1.refresh_from_db()
        self.assertEqual(task1.assigned_staff.count(), 2)
        self.assertIn(self.faculty1, task1.assigned_staff.all())
        self.assertIn(self.faculty2, task1.assigned_staff.all())

    def test_export_staff_tasks_csv(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

        response = self.client.get(reverse('staffs:export_staff_tasks_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

    def test_export_task_matrix_csv(self):
        session = self.client.session
        session['staff_id'] = self.hod.staff_id
        session.save()

    def test_technical_officer_role_dashboard_and_live_visualisation(self):
        to_staff = Staff.objects.create(
            staff_id="TECH001",
            name="Tech Officer",
            email="tech001@example.com",
            role="Technical Officer",
            is_profile_complete=True
        )
        session = self.client.session
        session['staff_id'] = to_staff.staff_id
        session.save()

        # Test Dashboard render using staffdash_technical.html
        response = self.client.get(reverse('staffs:staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staffdash_technical.html')

        # Test Access to Live Class Visualisation for Technical Officer
        vis_response = self.client.get(reverse('staffs:hod_live_class_visualisation'))
        self.assertEqual(vis_response.status_code, 200)

    def test_document_request_borrow_and_return_workflow(self):
        from students.models import DocumentRequest, Student
        
        # 1. Create Student & Office Staff
        student = Student.objects.create(
            roll_number="DOCSTUD01",
            student_name="Document Student",
            student_email="docstud@example.com",
            current_semester=4
        )
        office_staff = Staff.objects.create(
            staff_id="OFFICE01",
            name="Office Staff Member",
            email="office@example.com",
            role="Office Staff",
            is_profile_complete=True
        )

        # 2. Student applies for 10th Marksheet request
        session = self.client.session
        session['student_id'] = student.pk
        session['student_roll_number'] = student.roll_number
        session.save()

        apply_resp = self.client.post(reverse('apply_document_request'), {
            'document_type': '10th Marksheet',
            'reason': 'Required for Passport application',
            'expected_return_date': '2026-09-01'
        })
        self.assertEqual(apply_resp.status_code, 302)

        # Verify DocumentRequest created with status='Pending'
        doc_req = DocumentRequest.objects.get(student=student, document_type='10th Marksheet')
        self.assertEqual(doc_req.status, 'Pending')
        self.assertEqual(doc_req.reason, 'Required for Passport application')

        # 3. Office Staff views and marks as Ready for Collection
        session['staff_id'] = office_staff.staff_id
        session.save()

        ready_resp = self.client.post(reverse('staffs:office_manage_document_requests'), {
            'action': 'ready',
            'request_id': doc_req.id,
            'office_remarks': 'Document ready at counter 2'
        })
        self.assertEqual(ready_resp.status_code, 302)
        doc_req.refresh_from_db()
        self.assertEqual(doc_req.status, 'Ready for Collection')
        self.assertIsNotNone(doc_req.ready_at)

        # 4. Office Staff marks as Collected (Handed over to student)
        collected_resp = self.client.post(reverse('staffs:office_manage_document_requests'), {
            'action': 'collected',
            'request_id': doc_req.id
        })
        self.assertEqual(collected_resp.status_code, 302)
        doc_req.refresh_from_db()
        self.assertEqual(doc_req.status, 'Collected (Not Returned)')
        self.assertIsNotNone(doc_req.collected_at)

        # 5. Student returns physical document to office -> Office marks as Returned
        returned_resp = self.client.post(reverse('staffs:office_manage_document_requests'), {
            'action': 'returned',
            'request_id': doc_req.id
        })
        self.assertEqual(returned_resp.status_code, 302)
        doc_req.refresh_from_db()
        self.assertEqual(doc_req.status, 'Returned')
        self.assertIsNotNone(doc_req.returned_at)

    def test_scholarship_application_and_multi_filter_workflow(self):
        from students.models import ScholarshipApplication, Student, PersonalInfo, ScholarshipInfo
        
        # 1. Create Student & Scholarship Officer
        student = Student.objects.create(
            roll_number="SCHSTUD01",
            student_name="Scholarship Student",
            student_email="schstud@example.com",
            program_level="UG",
            current_semester=3
        )
        PersonalInfo.objects.create(
            student=student,
            community="BC",
            gender="Female",
            is_hosteler=True
        )
        officer = Staff.objects.create(
            staff_id="SCHOFF01",
            name="Scholarship Officer",
            email="schoff@example.com",
            role="Scholarship Officer",
            is_profile_complete=True
        )

        # 2. Student applies for BC/MBC Scholarship
        session = self.client.session
        session['student_pk'] = student.pk
        session['student_roll_number'] = student.roll_number
        session.save()

        apply_resp = self.client.post(reverse('apply_scholarship'), {
            'scholarship_type': 'BCMBC',
            'application_no': 'BC20269988',
            'annual_income': '180000',
            'income_certificate_no': 'INC-2026-99',
            'bank_account_no': '1234567890',
            'bank_ifsc': 'SBIN0001234'
        })
        self.assertEqual(apply_resp.status_code, 302)

        # Verify application created
        app = ScholarshipApplication.objects.get(student=student, scholarship_type='BCMBC')
        self.assertEqual(app.status, 'Pending Office Verification')
        self.assertEqual(app.annual_income, 180000)

        # 3. Test duplicate active application prevention
        dup_resp = self.client.post(reverse('apply_scholarship'), {
            'scholarship_type': 'BCMBC',
            'application_no': 'BC20269988'
        })
        self.assertEqual(dup_resp.status_code, 302)
        self.assertEqual(ScholarshipApplication.objects.filter(student=student, scholarship_type='BCMBC').count(), 1)

        # 4. Scholarship Officer uses multi-combination filter
        session['staff_id'] = officer.staff_id
        session.save()

        filter_url = reverse('staffs:scholarship_manager') + '?scholarship_types=BCMBC&community=BC&status=Pending+Office+Verification&max_income=250000'
        filter_resp = self.client.get(filter_url)
        self.assertEqual(filter_resp.status_code, 200)
        self.assertIn(app, filter_resp.context['applications'])

        # 5. Scholarship Officer approves application
        approve_resp = self.client.post(reverse('staffs:scholarship_manager'), {
            'action': 'approve',
            'app_id': app.id,
            'office_remarks': 'Verified against income certificate'
        })
        self.assertEqual(approve_resp.status_code, 302)

        app.refresh_from_db()
        self.assertEqual(app.status, 'Verified & Recommended')
        self.assertIsNotNone(app.verified_at)
        # Verify sync to ScholarshipInfo model
        sch_info = ScholarshipInfo.objects.get(student=student)
        self.assertTrue(sch_info.sch_bcmbc)

class ClassInchargeBatchTestCase(TestCase):
    def setUp(self):
        Staff.objects.all().delete()

    def test_whole_semester_class_incharge(self):
        ci = Staff.objects.create(
            staff_id="CI01",
            name="Whole Sem Incharge",
            email="ci01@example.com",
            role="Class Incharge",
            assigned_semester=3,
            assigned_batch="All"
        )
        ci.clean()
        self.assertEqual(ci.assigned_class_display, "Sem 3")

    def test_batch_a_and_b_separate_incharges(self):
        ci_a = Staff.objects.create(
            staff_id="CI_A",
            name="Batch A Incharge",
            email="cia@example.com",
            role="Class Incharge",
            assigned_semester=4,
            assigned_batch="A"
        )
        ci_a.clean()
        self.assertEqual(ci_a.assigned_class_display, "Sem 4 (Batch A)")

        ci_b = Staff.objects.create(
            staff_id="CI_B",
            name="Batch B Incharge",
            email="cib@example.com",
            role="Class Incharge",
            assigned_semester=4,
            assigned_batch="B"
        )
        ci_b.clean()
        self.assertEqual(ci_b.assigned_class_display, "Sem 4 (Batch B)")

    def test_batch_conflict_validation(self):
        Staff.objects.create(
            staff_id="CI_A",
            name="Batch A Incharge",
            email="cia@example.com",
            role="Class Incharge",
            assigned_semester=5,
            assigned_batch="A"
        )

        # Attempting to assign another Class Incharge to Batch A for Sem 5 should fail
        ci_a2 = Staff(
            staff_id="CI_A2",
            name="Another Batch A",
            email="cia2@example.com",
            role="Class Incharge",
            assigned_semester=5,
            assigned_batch="A"
        )
        with self.assertRaises(ValidationError):
            ci_a2.clean()

        # Attempting to assign Whole Sem when Batch A exists should fail
        ci_all = Staff(
            staff_id="CI_ALL",
            name="Whole Sem Incharge",
            email="ciall@example.com",
            role="Class Incharge",
            assigned_semester=5,
            assigned_batch="All"
        )
        with self.assertRaises(ValidationError):
            ci_all.clean()
