-- Seed data for fresh install. No ITAR/CUI/classified references.

-- COMPANIES ----------------------------------------------------------------
-- P1
INSERT INTO companies (name, location, type, priority, status) VALUES
    ('Boeing Defense', 'Oklahoma City, OK', 'prime', 1, 'researching'),
    ('Northrop Grumman', 'Oklahoma City, OK', 'prime', 1, 'researching');

-- P2
INSERT INTO companies (name, location, type, priority, status) VALUES
    ('Lockheed Martin Aeronautics', 'Fort Worth, TX', 'prime', 2, 'researching'),
    ('Pratt & Whitney (RTX)', 'Oklahoma City, OK', 'prime', 2, 'researching'),
    ('Spirit AeroSystems', 'Tulsa, OK', 'prime', 2, 'researching'),
    ('NORDAM', 'Tulsa, OK', 'prime', 2, 'researching'),
    ('KBR', 'Oklahoma City, OK', 'contractor', 2, 'researching'),
    ('Leidos', 'Oklahoma City, OK', 'contractor', 2, 'researching'),
    ('ATA Engineering', 'Remote', 'specialty', 2, 'researching');

-- P3
INSERT INTO companies (name, location, type, priority, status) VALUES
    ('BAE Systems', 'Oklahoma City, OK', 'contractor', 3, 'researching'),
    ('Sierra-7', 'Oklahoma City, OK', 'contractor', 3, 'researching'),
    ('Booz Allen Hamilton', 'Oklahoma City, OK', 'contractor', 3, 'researching'),
    ('Stress Engineering Services', 'Remote', 'specialty', 3, 'researching'),
    ('Veryst Engineering', 'Remote', 'specialty', 3, 'researching'),
    ('ESRD', 'Remote', 'specialty', 3, 'researching'),
    ('SpaceX', 'Hawthorne, CA', 'newspace', 3, 'researching'),
    ('Blue Origin', 'Kent, WA', 'newspace', 3, 'researching'),
    ('Sikorsky (Lockheed Martin)', 'Stratford, CT', 'prime', 3, 'researching');

-- ACTIONS ------------------------------------------------------------------
-- 30-day high priority
INSERT INTO actions (title, category, priority, target_date, status) VALUES
    ('Email security manager re: clearance status and renewal timeline', 'clearance', 'high', date('now','+7 days'), 'pending'),
    ('Reply to AIAA Engage thread (intro post / recent activity)', 'membership', 'high', date('now','+10 days'), 'pending'),
    ('Inquire about ODIA membership pricing and event calendar', 'membership', 'high', date('now','+14 days'), 'pending'),
    ('Activate AIAA professional membership (transition from student/none)', 'membership', 'high', date('now','+21 days'), 'pending'),
    ('Identify 5 LinkedIn target contacts at P1/P2 companies and send connections', 'network', 'high', date('now','+21 days'), 'pending'),
    ('Set up Obsidian vault folder structure (career, technical, books, lessons)', 'admin', 'high', date('now','+7 days'), 'pending'),
    ('Draft 5 project story stubs (S/T/A/R/Technical headings only, ~3 sentences each)', 'interview', 'high', date('now','+30 days'), 'pending');

-- 90-day medium priority
INSERT INTO actions (title, category, priority, target_date, status) VALUES
    ('Lunch with 2 industry-transplant colleagues (gov->industry route)', 'network', 'medium', date('now','+60 days'), 'pending'),
    ('Write polished version of E-6 engine cowl panel story (low edge distance)', 'interview', 'medium', date('now','+60 days'), 'pending'),
    ('Write polished version of cold-worked bushed interference-fit hole story', 'interview', 'medium', date('now','+75 days'), 'pending'),
    ('Attend first ODIA or AIAA-OK event in person', 'network', 'medium', date('now','+75 days'), 'pending'),
    ('Begin Bruhn — read chapters C7 through C13 (cutout/joint/skin-stringer)', 'learning', 'medium', date('now','+90 days'), 'pending'),
    ('Begin Bannantine/Stephens — strain-life fatigue fundamentals', 'learning', 'medium', date('now','+90 days'), 'pending'),
    ('Buy Roark''s Formulas for Stress and Strain', 'learning', 'medium', date('now','+30 days'), 'pending'),
    ('Buy Flabel — Practical Stress Analysis for Design Engineers', 'learning', 'medium', date('now','+30 days'), 'pending'),
    ('Buy Voss — Aircraft Stress Analysis and Sizing', 'learning', 'medium', date('now','+30 days'), 'pending');

-- 365-day medium priority
INSERT INTO actions (title, category, priority, target_date, status) VALUES
    ('Take on volunteer role with AIAA-OK section (event lead or committee)', 'network', 'medium', date('now','+365 days'), 'pending'),
    ('First informational outreach call to industry-side stress engineer', 'network', 'medium', date('now','+180 days'), 'pending'),
    ('Complete all 5 project stories at "polished" readiness', 'interview', 'medium', date('now','+270 days'), 'pending'),
    ('Draft sustainment-focused resume version (E-6 / depot / EDSM emphasis)', 'resume', 'medium', date('now','+180 days'), 'pending'),
    ('Draft broad-airframe resume version (Bruhn, fatigue, FEA emphasis)', 'resume', 'medium', date('now','+270 days'), 'pending'),
    ('H1B disclosure salary pull for OKC/Tulsa/DFW stress engineer roles', 'salary_research', 'medium', date('now','+120 days'), 'pending'),
    ('Cut target company list from 18 to 8-10 by quality of fit', 'admin', 'medium', date('now','+150 days'), 'pending');

-- LEARNING ITEMS -----------------------------------------------------------
-- P1
INSERT INTO learning_items (type, title, author, priority, status, tags) VALUES
    ('book', 'Analysis and Design of Flight Vehicle Structures', 'E. F. Bruhn', 1, 'queued', 'airframe,structural,canonical'),
    ('book', 'Practical Stress Analysis for Design Engineers', 'Jean-Claude Flabel', 1, 'queued', 'practical,hand-calc'),
    ('book', 'Roark''s Formulas for Stress and Strain', 'Young, Budynas, Sadegh', 1, 'queued', 'reference,formulas'),
    ('book', 'Aircraft Stress Analysis and Sizing', 'Maan Voss', 1, 'queued', 'airframe,sizing');

-- P2
INSERT INTO learning_items (type, title, author, priority, status, tags) VALUES
    ('book', 'Fundamentals of Metal Fatigue Analysis', 'Bannantine, Comer, Handrock', 2, 'queued', 'fatigue,strain-life'),
    ('book', 'Metal Fatigue in Engineering', 'Stephens, Fatemi, Stephens, Fuchs', 2, 'queued', 'fatigue,da-dt'),
    ('book', 'Airframe Stress Analysis and Sizing', 'Michael C.Y. Niu', 2, 'queued', 'airframe,composites'),
    ('reference', 'FAA AC 25.571 — Damage Tolerance and Fatigue Evaluation', 'FAA', 2, 'queued', 'reg,fatigue,da-dt'),
    ('reference', 'MMPDS — Metallic Materials Properties Development and Standardization', 'BattellE/FAA', 2, 'queued', 'materials,allowables');

-- P3
INSERT INTO learning_items (type, title, author, priority, status, tags) VALUES
    ('book', 'Aircraft Structures', 'David J. Peery', 3, 'queued', 'classic,airframe'),
    ('book', 'Aircraft Structures for Engineering Students', 'T. H. G. Megson', 3, 'queued', 'classic,airframe'),
    ('book', 'Finite Element Modeling for Stress Analysis', 'Robert D. Cook', 3, 'queued', 'fea,theory'),
    ('reference', 'NASGRO Reference Manual', 'SwRI/NASA', 3, 'queued', 'da-dt,fracture');

-- PROJECT STORIES (titles + empty stub fields) -----------------------------
INSERT INTO project_stories (title, problem_domain, readiness) VALUES
    ('E-6 engine cowl panel countersunk hole EDSM — low edge distance', 'sustainment / disposition', 'draft'),
    ('Cold-worked bushed interference-fit hole — StressCheck quarter-plate model', 'FEA / fatigue', 'draft'),
    ('[Third — fatigue/DaDT]', 'fatigue', 'draft'),
    ('[Fourth — MoS defense]', 'static / sizing', 'draft'),
    ('[Fifth — process/tool improvement]', 'process', 'draft');
