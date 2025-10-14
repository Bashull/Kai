import { describe, it, expect, beforeAll } from 'vitest';
import request from 'supertest';
import app from './server';

describe('GET /status', () => {
  beforeAll(() => {
    // Ensure we're in test mode
    process.env.NODE_ENV = 'test';
  });

  it('should return 200 status code', async () => {
    const response = await request(app).get('/status');
    expect(response.status).toBe(200);
  });

  it('should return JSON content type', async () => {
    const response = await request(app).get('/status');
    expect(response.headers['content-type']).toMatch(/json/);
  });

  it('should return status "ok"', async () => {
    const response = await request(app).get('/status');
    expect(response.body.status).toBe('ok');
  });

  it('should return mode from environment', async () => {
    const response = await request(app).get('/status');
    expect(response.body.mode).toBeDefined();
    expect(typeof response.body.mode).toBe('string');
    // In test environment, mode should be 'test'
    expect(response.body.mode).toBe('test');
  });

  it('should return uptime as a number', async () => {
    const response = await request(app).get('/status');
    expect(response.body.uptime).toBeDefined();
    expect(typeof response.body.uptime).toBe('number');
    expect(response.body.uptime).toBeGreaterThanOrEqual(0);
  });

  it('should return memory information', async () => {
    const response = await request(app).get('/status');
    expect(response.body.memory).toBeDefined();
    expect(typeof response.body.memory).toBe('object');
    
    // Check memory properties
    expect(response.body.memory.rss).toBeDefined();
    expect(typeof response.body.memory.rss).toBe('number');
    expect(response.body.memory.rss).toBeGreaterThan(0);
    
    expect(response.body.memory.heapTotal).toBeDefined();
    expect(typeof response.body.memory.heapTotal).toBe('number');
    expect(response.body.memory.heapTotal).toBeGreaterThan(0);
    
    expect(response.body.memory.heapUsed).toBeDefined();
    expect(typeof response.body.memory.heapUsed).toBe('number');
    expect(response.body.memory.heapUsed).toBeGreaterThan(0);
    
    expect(response.body.memory.external).toBeDefined();
    expect(typeof response.body.memory.external).toBe('number');
    expect(response.body.memory.external).toBeGreaterThanOrEqual(0);
  });

  it('should return timestamp in ISO format', async () => {
    const response = await request(app).get('/status');
    expect(response.body.timestamp).toBeDefined();
    expect(typeof response.body.timestamp).toBe('string');
    
    // Validate ISO 8601 format
    const timestamp = new Date(response.body.timestamp);
    expect(timestamp.toISOString()).toBe(response.body.timestamp);
  });

  it('should not expose sensitive information', async () => {
    const response = await request(app).get('/status');
    
    // Ensure no sensitive data is in the response
    expect(response.body.apiKey).toBeUndefined();
    expect(response.body.password).toBeUndefined();
    expect(response.body.secret).toBeUndefined();
    expect(response.body.token).toBeUndefined();
    expect(response.body.env).toBeUndefined();
  });

  it('should have consistent structure on multiple calls', async () => {
    const response1 = await request(app).get('/status');
    const response2 = await request(app).get('/status');
    
    expect(Object.keys(response1.body).sort()).toEqual(Object.keys(response2.body).sort());
    expect(response2.body.uptime).toBeGreaterThanOrEqual(response1.body.uptime);
  });
});

describe('GET /health', () => {
  it('should return 200 status code', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
  });

  it('should return status "ok"', async () => {
    const response = await request(app).get('/health');
    expect(response.body.status).toBe('ok');
  });
});
