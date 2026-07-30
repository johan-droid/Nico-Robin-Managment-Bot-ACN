use std::fmt::Write;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

static NEXT_TRACE_ID: AtomicU64 = AtomicU64::new(1);

pub fn next_trace_id() -> u64 {
    NEXT_TRACE_ID.fetch_add(1, Ordering::Relaxed)
}

pub struct Timer {
    start: Instant,
}

impl Timer {
    pub fn start(_label: &'static str) -> Self {
        Self {
            start: Instant::now(),
        }
    }

    pub fn stop(self) -> u64 {
        self.start.elapsed().as_micros() as u64
    }
}

thread_local! {
    static TRACE: std::cell::RefCell<Option<LatencyTrace>> = const { std::cell::RefCell::new(None) };
}

pub struct LatencyTrace {
    pub trace_id: u64,
    entries: Vec<TraceEntry>,
}

struct TraceEntry {
    label: &'static str,
    elapsed_us: u64,
}

impl LatencyTrace {
    pub fn begin(trace_id: u64) {
        TRACE.with(|t| {
            *t.borrow_mut() = Some(LatencyTrace {
                trace_id,
                entries: Vec::with_capacity(32),
            })
        });
    }

    pub fn record(label: &'static str, elapsed_us: u64) {
        TRACE.with(|t| {
            if let Some(ref mut trace) = *t.borrow_mut() {
                trace.entries.push(TraceEntry { label, elapsed_us });
            }
        });
    }

    pub fn finish() {
        TRACE.with(|t| {
            let trace = t.borrow_mut().take();
            if let Some(trace) = trace {
                if trace.entries.is_empty() {
                    return;
                }
                let total = trace.entries.last().map(|e| e.elapsed_us).unwrap_or(0);
                let mut report = String::with_capacity(512);
                let _ = writeln!(report, "[Perf] trace={} total={}µs", trace.trace_id, total);
                for entry in &trace.entries {
                    let pct = if total > 0 {
                        (entry.elapsed_us as f64 / total as f64) * 100.0
                    } else {
                        0.0
                    };
                    let _ = writeln!(
                        report,
                        "  {:<40} {:>8}µs ({:5.1}%)",
                        entry.label, entry.elapsed_us, pct
                    );
                }
                tracing::debug!("{}", report.trim_end());
            }
        });
    }
}
