-- DEMO bookings + payments. Run in the Supabase SQL editor.
-- Safe to re-run: it wipes and reseeds ONLY these two demo tables.
-- Swap these for your real tables later; only app/tools.py touches them.

create table if not exists bookings (
  id text primary key,                                   -- e.g. 'F1001'
  customer_id uuid not null,
  court text not null,
  start_time timestamptz not null,
  duration_hours int not null default 1,
  amount numeric not null,
  status text not null check (status in ('confirmed','pending','cancelled')),
  created_at timestamptz not null default now()
);

create table if not exists payments (
  txn_id text primary key,                               -- e.g. 'TXN1001'
  customer_id uuid not null,
  booking_id text references bookings(id),               -- NULL = money taken, no booking created
  amount numeric not null,
  provider text not null,                                -- esewa | khalti
  status text not null check (status in ('success','pending','failed')),
  created_at timestamptz not null default now()
);

-- No policies + RLS on = only the service key (your backend) can read these.
alter table bookings enable row level security;
alter table payments enable row level security;

delete from payments;
delete from bookings;

-- Demo customers (use these as customer_id in test requests):
--   Alice 11111111-1111-1111-1111-111111111111   all good, plus one failed payment
--   Bob   22222222-2222-2222-2222-222222222222   paid, NO booking created   <- the headline case
--   Carol 33333333-3333-3333-3333-333333333333   charged twice for one booking
--   Dave  44444444-4444-4444-4444-444444444444   payment + booking still pending

insert into bookings (id, customer_id, court, start_time, duration_hours, amount, status) values
 ('F1001','11111111-1111-1111-1111-111111111111','5-a-side Court A', now() + interval '1 day', 1, 1800,'confirmed'),
 ('F3001','33333333-3333-3333-3333-333333333333','7-a-side Court B', now() + interval '2 days',1, 2500,'confirmed'),
 ('F4001','44444444-4444-4444-4444-444444444444','5-a-side Court A', now() + interval '3 days',1, 1800,'pending');

insert into payments (txn_id, customer_id, booking_id, amount, provider, status, created_at) values
 ('TXN1001','11111111-1111-1111-1111-111111111111','F1001',1800,'esewa', 'success', now() - interval '2 hours'),
 ('TXN1002','11111111-1111-1111-1111-111111111111', null,  1800,'khalti','failed',  now() - interval '1 day'),
 ('TXN2001','22222222-2222-2222-2222-222222222222', null,  1800,'esewa', 'success', now() - interval '1 day'),
 ('TXN3001','33333333-3333-3333-3333-333333333333','F3001',2500,'khalti','success', now() - interval '3 hours'),
 ('TXN3002','33333333-3333-3333-3333-333333333333','F3001',2500,'khalti','success', now() - interval '179 minutes'),
 ('TXN4001','44444444-4444-4444-4444-444444444444','F4001',1800,'esewa', 'pending', now() - interval '10 minutes');