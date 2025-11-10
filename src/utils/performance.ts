/**
 * Performance Monitoring Utilities
 * 
 * Utilities for tracking and monitoring application performance
 */

interface PerformanceMetric {
  name: string;
  duration: number;
  timestamp: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private marks: Map<string, number> = new Map();

  /**
   * Start measuring a performance metric
   */
  start(name: string): void {
    this.marks.set(name, performance.now());
  }

  /**
   * End measuring a performance metric
   */
  end(name: string): number | null {
    const startTime = this.marks.get(name);
    if (!startTime) {
      console.warn(`Performance mark "${name}" not found`);
      return null;
    }

    const duration = performance.now() - startTime;
    this.metrics.push({
      name,
      duration,
      timestamp: Date.now(),
    });

    this.marks.delete(name);
    return duration;
  }

  /**
   * Measure a function execution time
   */
  async measure<T>(name: string, fn: () => T | Promise<T>): Promise<T> {
    this.start(name);
    try {
      const result = await fn();
      this.end(name);
      return result;
    } catch (error) {
      this.end(name);
      throw error;
    }
  }

  /**
   * Get all metrics
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Get metrics by name
   */
  getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter(m => m.name === name);
  }

  /**
   * Get average duration for a metric
   */
  getAverageDuration(name: string): number {
    const metrics = this.getMetricsByName(name);
    if (metrics.length === 0) return 0;
    
    const total = metrics.reduce((sum, m) => sum + m.duration, 0);
    return total / metrics.length;
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = [];
    this.marks.clear();
  }

  /**
   * Get performance summary
   */
  getSummary(): Record<string, { count: number; avg: number; min: number; max: number }> {
    const summary: Record<string, { count: number; avg: number; min: number; max: number }> = {};
    
    this.metrics.forEach(metric => {
      if (!summary[metric.name]) {
        summary[metric.name] = {
          count: 0,
          avg: 0,
          min: Infinity,
          max: -Infinity,
        };
      }
      
      const s = summary[metric.name];
      s.count++;
      s.min = Math.min(s.min, metric.duration);
      s.max = Math.max(s.max, metric.duration);
    });

    Object.keys(summary).forEach(name => {
      const metrics = this.getMetricsByName(name);
      summary[name].avg = this.getAverageDuration(name);
    });

    return summary;
  }

  /**
   * Log performance summary to console
   */
  logSummary(): void {
    const summary = this.getSummary();
    console.table(summary);
  }
}

// Create singleton instance
export const performanceMonitor = new PerformanceMonitor();

/**
 * Web Vitals monitoring
 */
export const measureWebVitals = () => {
  // First Contentful Paint
  const paintEntries = performance.getEntriesByType('paint');
  const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint');
  
  if (fcp) {
    console.log('First Contentful Paint:', fcp.startTime, 'ms');
  }

  // Largest Contentful Paint (if supported)
  if ('PerformanceObserver' in window) {
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        console.log('Largest Contentful Paint:', lastEntry.startTime, 'ms');
      });
      observer.observe({ entryTypes: ['largest-contentful-paint'] });
    } catch (e) {
      // LCP not supported
    }
  }

  // Navigation timing
  const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  if (navigation) {
    console.log('DOM Content Loaded:', navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart, 'ms');
    console.log('Load Complete:', navigation.loadEventEnd - navigation.loadEventStart, 'ms');
  }
};

/**
 * Monitor component render performance
 */
export const useRenderPerformance = (componentName: string) => {
  if (process.env.NODE_ENV === 'development') {
    const renderStart = performance.now();
    
    return () => {
      const renderEnd = performance.now();
      const duration = renderEnd - renderStart;
      
      if (duration > 16) { // Longer than 1 frame at 60fps
        console.warn(`${componentName} render took ${duration.toFixed(2)}ms`);
      }
    };
  }
  
  return () => {};
};

/**
 * Debounced performance logger
 */
let logTimeout: NodeJS.Timeout;
export const logPerformanceMetric = (name: string, duration: number) => {
  performanceMonitor.metrics.push({
    name,
    duration,
    timestamp: Date.now(),
  });

  clearTimeout(logTimeout);
  logTimeout = setTimeout(() => {
    if (process.env.NODE_ENV === 'development') {
      performanceMonitor.logSummary();
    }
  }, 5000);
};

export default performanceMonitor;
