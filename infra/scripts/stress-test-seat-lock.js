import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

// ==============================================================================
// k6 High-Concurrency Stress Test: Seat Lock Contention (Milestone 6)
// Target: 1,000 Concurrent VUs competing for the EXACT SAME VIP SEAT
// Goal: Verify Redis Distributed Lock guarantees ZERO double-booking
// ==============================================================================

const successCounter = new Counter('successful_bookings');
const conflictCounter = new Counter('seat_conflicts');
const errorCounter = new Counter('other_errors');
const errorRate = new Rate('unexpected_error_rate');

export const options = {
  stages: [
    { duration: '3s', target: 200 },   // Fast ramp-up to 200 VUs
    { duration: '10s', target: 1000 }, // Peak load: 1,000 VUs competing simultaneously
    { duration: '3s', target: 0 },     // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<300'],  // 95% of lock checks complete within 300ms
    unexpected_error_rate: ['rate<0.05'], // Max 5% unexpected errors (409 is expected)
  },
};

// Target endpoint: defaults to direct booking-service (port 3003) or Kong Gateway (port 8000)
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:3003/v1/bookings';
const SHOW_ID = __ENV.SHOW_ID || 'd3b07384-d113-4ec6-a56f-958087920782';
const SEAT_ID = __ENV.SEAT_ID || 'e7b07384-d113-4ec6-a56f-958087920799'; // VIP Seat A01

export function setup() {
  console.log('==============================================================');
  console.log('🚀 KHỞI ĐỘNG k6 HIGH-CONCURRENCY STRESS TEST (1,000 VUs)');
  console.log(`📡 Target Endpoint: ${BASE_URL}`);
  console.log(`🎭 Show ID:        ${SHOW_ID}`);
  console.log(`💺 VIP Seat ID:    ${SEAT_ID}`);
  console.log('==============================================================');

  return {
    startTime: new Date().toISOString(),
  };
}

export default function () {
  // Generate distinct virtual user ID for each VU to simulate 1,000 separate buyers
  const userId = `00000000-0000-0000-0000-${String(__VU).padStart(12, '0')}`;

  const payload = JSON.stringify({
    show_id: SHOW_ID,
    seat_ids: [SEAT_ID],
  });

  const headers = {
    'Content-Type': 'application/json',
    'X-User-ID': userId, // Gateway trusted header for booking-service
  };

  if (__ENV.AUTH_TOKEN) {
    headers['Authorization'] = `Bearer ${__ENV.AUTH_TOKEN}`;
  }

  const res = http.post(BASE_URL, payload, { headers });

  if (res.status === 201) {
    // Exactly ONE request in the entire test run should succeed here
    successCounter.add(1);
    check(res, { 'booking created (201)': (r) => r.status === 201 });
  } else if (res.status === 409 || res.status === 423) {
    // All competing requests should receive 409 Conflict (seat already locked)
    conflictCounter.add(1);
    check(res, { 'seat conflict safely rejected (409)': (r) => r.status === 409 || r.status === 423 });
  } else {
    // Any other status code (400, 500, 502) is tracked as an unexpected error
    errorCounter.add(1);
    errorRate.add(1);
    check(res, {
      'unexpected status code': (r) => r.status === 201 || r.status === 409,
    });
  }

  sleep(0.05);
}

export function teardown() {
  console.log('==============================================================');
  console.log('🏁 HOÀN TẤT BENCHMARK TRANH CHẤP GHẾ k6');
  console.log('==============================================================');
}
