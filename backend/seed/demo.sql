-- TeamUp demo data, ported from the frontend's src/api/mock.js so the demo doesn't start empty.
-- Times are relative to the moment the data is loaded, so it always looks recent.
--
--   python -m app.seed            load it (only when the database has no users yet)
--   python -m app.seed --reset    DELETE EVERYTHING, then load it again
--
-- Demo students can be used as logins only in local dev mode (AUTH_MODE=dev), e.g. the token
-- "dev:john.carter@student.uni.ac.th" (John is the admin). With Cognito, register real accounts.

INSERT INTO categories (name, created_at) VALUES
  ('Course Project', now() - interval '5 minutes'),
  ('Competition',    now() - interval '4 minutes'),
  ('Senior Project', now() - interval '3 minutes'),
  ('Startup Idea',   now() - interval '2 minutes'),
  ('Research',       now() - interval '1 minute')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------- students
INSERT INTO users (id, email, name, student_id, major, year, role, status, bio, portfolio,
                   notify_invitations, notify_requests, notify_team, notify_digest, created_at)
VALUES (1, 'john.carter@student.uni.ac.th', 'John Carter', '6600123456', 'Digital Engineering', 3, 'admin', 'active',
        'UI/UX-focused developer who loves turning messy requirements into clean interfaces.', 'github.com/johncarter',
        true, true, false, true, now() - interval '86 days');

-- Students 2-18: student ID = 6600000000 + id * 111; joined between 82 and 18 days ago.
INSERT INTO users (id, email, name, student_id, major, year, status, created_at)
SELECT id, email, name, (6600000000 + id * 111)::text, major, year, status, now() - make_interval(days => 90 - id * 4)
FROM (VALUES
  (2,  'emma.wilson@student.uni.ac.th',     'Emma Wilson',     'Computer Engineering',   3, 'active'),
  (3,  'lucas.brown@student.uni.ac.th',     'Lucas Brown',     'Digital Engineering',    2, 'active'),
  (4,  'daniel.ortiz@student.uni.ac.th',    'Daniel Ortiz',    'Computer Engineering',   4, 'active'),
  (5,  'oliver.smith@student.uni.ac.th',    'Oliver Smith',    'Computer Engineering',   3, 'active'),
  (6,  'sophia.martinez@student.uni.ac.th', 'Sophia Martinez', 'Digital Engineering',    3, 'active'),
  (7,  'ethan.johnson@student.uni.ac.th',   'Ethan Johnson',   'Information Technology', 2, 'active'),
  (8,  'liam.garcia@student.uni.ac.th',     'Liam Garcia',     'Computer Engineering',   4, 'active'),
  (9,  'ava.thompson@student.uni.ac.th',    'Ava Thompson',    'Digital Engineering',    2, 'active'),
  (10, 'noah.davis@student.uni.ac.th',      'Noah Davis',      'Industrial Engineering', 3, 'active'),
  (11, 'grace.hall@student.uni.ac.th',      'Grace Hall',      'Data Science',           3, 'active'),
  (12, 'ryan.king@student.uni.ac.th',       'Ryan King',       'Computer Engineering',   2, 'active'),
  (13, 'henry.moore@student.uni.ac.th',     'Henry Moore',     'Business Technology',    4, 'active'),
  (14, 'chloe.kim@student.uni.ac.th',       'Chloe Kim',       'Computer Engineering',   3, 'active'),
  (15, 'mia.turner@student.uni.ac.th',      'Mia Turner',      'Mechanical Engineering', 4, 'active'),
  (16, 'leo.adams@student.uni.ac.th',       'Leo Adams',       'Electrical Engineering', 3, 'active'),
  (17, 'zoe.baker@student.uni.ac.th',       'Zoe Baker',       'Computer Engineering',   3, 'active'),
  (18, 'jack.scott@student.uni.ac.th',      'Jack Scott',      'Information Technology', 2, 'suspended')
) AS v(id, email, name, major, year, status);

INSERT INTO user_skills (user_id, name, level, position) VALUES
  (1, 'React', 'Advanced', 0), (1, 'UI/UX Design', 'Advanced', 1), (1, 'Figma', 'Advanced', 2),
  (1, 'JavaScript', 'Intermediate', 3), (1, 'Python', 'Intermediate', 4), (1, 'SQL', 'Beginner', 5);

-- Everyone else's skills at Intermediate; unnest ... WITH ORDINALITY keeps the listed order.
INSERT INTO user_skills (user_id, name, level, position)
SELECT v.user_id, s.name, 'Intermediate', s.ord - 1
FROM (VALUES
  (2,  ARRAY['FastAPI', 'PostgreSQL', 'Python']),
  (3,  ARRAY['SQL', 'Pytest', 'Python']),
  (4,  ARRAY['AWS', 'Docker', 'Linux']),
  (5,  ARRAY['React', 'JavaScript', 'Figma']),
  (6,  ARRAY['Figma', 'UI/UX Design', 'React']),
  (7,  ARRAY['React', 'Node.js', 'SQL']),
  (8,  ARRAY['UI/UX Design', 'Flutter', 'Python']),
  (9,  ARRAY['JavaScript', 'Vue.js', 'CSS']),
  (10, ARRAY['UI/UX Design', 'Research']),
  (11, ARRAY['Python', 'Pandas', 'D3.js']),
  (12, ARRAY['JavaScript', 'React']),
  (13, ARRAY['Figma', 'Product']),
  (14, ARRAY['Flutter', 'Firebase']),
  (15, ARRAY['C++', 'Arduino', 'CAD']),
  (16, ARRAY['Arduino', 'C++']),
  (17, ARRAY['Python', 'C++']),
  (18, ARRAY['Node.js', 'Firebase'])
) AS v(user_id, skills)
CROSS JOIN LATERAL unnest(v.skills) WITH ORDINALITY AS s(name, ord);

INSERT INTO user_interests (user_id, name, position) VALUES
  (1, 'Web Development', 0), (1, 'Sustainability', 1), (1, 'EdTech', 2);

-- ---------------------------------------------------------------- projects
INSERT INTO projects (id, owner_id, title, description, category, course, max_size, accepting, deadline, duration, meeting, created_at) VALUES
  (1, 1, 'Campus Food Waste Tracker',
   'Canteens on campus throw away a surprising amount of food every day, but nobody measures it. We’re building a web app where canteen staff log leftovers in under 30 seconds and everyone sees weekly dashboards. Goal: cut food waste by 20% this semester.',
   'Course Project', 'DES424 Cloud-based App Dev', 5, true, current_date + 21, 'Aug – Dec 2026', 'On campus, 2× / week', now() - interval '26 days'),
  (2, 5, 'AI Study Buddy Chatbot',
   'An LLM-powered chatbot that turns lecture slides into quizzes and flashcards for exam revision.',
   'Competition', 'National AI Hackathon', 4, true, current_date + 1, 'Oct – Nov 2026', 'Online, weekends', now() - interval '9 days'),
  (3, 7, 'Smart Parking IoT System',
   'Sensor network that shows free parking spots around campus in real time via a mobile web app.',
   'Senior Project', '', 5, true, current_date + 36, 'Full academic year', 'Lab, Tue & Thu', now() - interval '14 days'),
  (4, 11, 'City Air Quality Viz',
   'Interactive map visualizing PM2.5 history and forecasts for city districts using open data.',
   'Research', '', 3, true, current_date + 11, '8 weeks', 'Online, flexible', now() - interval '3 days'),
  (5, 13, 'Mobile Health Reminder',
   'Medication and appointment reminder app for elderly users with caregiver notifications.',
   'Startup Idea', '', 4, true, current_date + 22, 'Ongoing', 'Co-working space, Fridays', now() - interval '5 hours'),
  (6, 15, 'Robotics Challenge Team',
   'Build an autonomous line-following robot for the national university robotics challenge.',
   'Competition', '', 3, false, current_date - 39, 'Sep – Dec 2026', 'Workshop, daily', now() - interval '40 days'),
  -- Two reported spam projects, so the admin page has something to moderate.
  (7, 18, 'CRYPTO PUMP GROUP',
   'Join our crypto signals group and get rich fast! Message us for the invite link.',
   'Startup Idea', '', 5, false, NULL, '—', '—', now() - interval '2 days'),
  (8, 14, 'Easy A — We Do Your Assignment',
   'Send us your assignment brief and we hand in a finished report for you.',
   'Course Project', '', 3, false, NULL, '—', '—', now() - interval '4 days');

INSERT INTO project_skills (project_id, name, position)
SELECT v.project_id, s.name, s.ord - 1
FROM (VALUES
  (1, ARRAY['React', 'FastAPI', 'PostgreSQL', 'AWS']),
  (2, ARRAY['Python', 'NLP', 'React', 'UI/UX Design']),
  (3, ARRAY['Python', 'IoT', 'AWS', 'SQL']),
  (4, ARRAY['Python', 'Pandas', 'D3.js', 'JavaScript']),
  (5, ARRAY['Flutter', 'Figma', 'UI/UX Design', 'Firebase']),
  (6, ARRAY['C++', 'Arduino', 'CAD', 'Python']),
  (7, ARRAY['Crypto', 'Marketing']),
  (8, ARRAY['Writing'])
) AS v(project_id, skills)
CROSS JOIN LATERAL unnest(v.skills) WITH ORDINALITY AS s(name, ord);

-- Team places: the owner's place first; user_id NULL = an open spot.
INSERT INTO project_roles (project_id, name, user_id, position) VALUES
  (1, 'UI/UX Designer', 1, 0), (1, 'Backend Developer', 2, 1), (1, 'Data & QA', 3, 2), (1, 'Cloud Engineer', 4, 3),
  (1, 'Frontend Developer', NULL, 4),
  (2, 'ML Engineer', 5, 0), (2, 'Backend Developer', 6, 1), (2, 'UI/UX Designer', 1, 2), (2, 'Frontend Developer', NULL, 3),
  (3, 'IoT Engineer', 7, 0), (3, 'Backend Developer', 8, 1), (3, 'Data Analyst', 9, 2), (3, 'Hardware', 10, 3),
  (3, 'Cloud Engineer', NULL, 4),
  (4, 'Data Scientist', 11, 0), (4, 'Frontend Developer', 12, 1), (4, 'Data Analyst', NULL, 2),
  (5, 'Product Lead', 13, 0), (5, 'Mobile Developer', 14, 1), (5, 'UI/UX Designer', NULL, 2), (5, 'Backend Developer', NULL, 3),
  (6, 'Team Lead', 15, 0), (6, 'Hardware', 16, 1), (6, 'Software', 17, 2),
  (7, 'Founder', 18, 0), (7, 'Promoter', NULL, 1),
  (8, 'Owner', 14, 0), (8, 'Writer', NULL, 1);

-- ---------------------------------------------------------------- requests, invitations, saves, reports
INSERT INTO requests (id, project_id, user_id, by_id, kind, role, message, status, created_at, responded_at) VALUES
  (1, 1, 5, NULL, 'request', 'Frontend Developer',
   'I’ve built two React dashboards for my internship and would love to help with the charts.', 'pending',
   now() - interval '12 minutes', NULL),
  (2, 1, 7, NULL, 'request', 'Frontend Developer', 'I want to improve my React skills on a real project.', 'pending',
   now() - interval '3 hours', NULL),
  (3, 5, 1, 13, 'invitation', 'UI/UX Designer',
   'Your Figma portfolio is great — we need someone to design our reminder screens!', 'pending',
   now() - interval '1 hour', NULL),
  (4, 6, 1, NULL, 'request', 'Software', 'I can help with the dashboard for sensor data.', 'rejected',
   now() - interval '26 days', now() - interval '25 days'),
  (5, 1, 3, NULL, 'request', 'Data & QA', 'Happy to own testing.', 'accepted',
   now() - interval '21 days', now() - interval '20 days'),
  (6, 1, 6, 1, 'invitation', 'Frontend Developer', 'Would love your help on the dashboard UI.', 'pending',
   now() - interval '1 day', NULL);

INSERT INTO saved_projects (user_id, project_id) VALUES (1, 2);

INSERT INTO reports (project_id, reporter_id, reason, created_at) VALUES
  (7, 3, 'Spam / scam', now() - interval '20 hours'),
  (7, 4, 'Spam / scam', now() - interval '30 hours'),
  (7, 5, 'Spam / scam', now() - interval '40 hours'),
  (8, 2, 'Academic dishonesty', now() - interval '3 days'),
  (8, 6, 'Academic dishonesty', now() - interval '4 days');

-- ---------------------------------------------------------------- notifications
INSERT INTO notifications (user_id, kind, text, request_id, unread, created_at) VALUES
  (1, 'request', 'Oliver Smith requested to join Campus Food Waste Tracker as Frontend Developer.', 1, true, now() - interval '12 minutes'),
  (1, 'invite', 'Henry Moore invited you to join Mobile Health Reminder as UI/UX Designer.', 3, true, now() - interval '1 hour'),
  (1, 'request', 'Ethan Johnson requested to join Campus Food Waste Tracker as Frontend Developer.', 2, true, now() - interval '3 hours'),
  (1, 'accepted', 'Your request to join AI Study Buddy Chatbot was accepted. Say hi to your new team!', NULL, false, now() - interval '26 hours'),
  (1, 'team', 'Lucas Brown joined Campus Food Waste Tracker as Data & QA.', NULL, false, now() - interval '2 days'),
  (1, 'declined', 'Your request to join Robotics Challenge Team was declined. The team is now complete.', NULL, false, now() - interval '26 days'),
  (1, 'match', '3 new projects match your skills: React, UI/UX Design, Figma.', NULL, false, now() - interval '27 days'),
  (6, 'invite', 'John Carter invited you to join Campus Food Waste Tracker as Frontend Developer.', 6, true, now() - interval '1 day');

-- New rows created through the app continue after the demo ids.
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT max(id) FROM users));
SELECT setval(pg_get_serial_sequence('projects', 'id'), (SELECT max(id) FROM projects));
SELECT setval(pg_get_serial_sequence('requests', 'id'), (SELECT max(id) FROM requests));
