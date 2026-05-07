pub trait RoundToNthDigit {
    fn round_to_nth_digit(&self, nth: usize) -> Self;
    fn round_to_2_digit(&self) -> Self;
    fn round_to_3_digit(&self) -> Self;
    fn round_to_4_digit(&self) -> Self;
}

impl RoundToNthDigit for f64 {
    fn round_to_nth_digit(&self, nth: usize) -> f64 {
        let scale = 10_f64.powi(nth as i32);
        let scaled = *self * scale;
        (scaled).round() / scale
    }

    fn round_to_2_digit(&self) -> f64 {
        (*self * 100.0).round() / 100.0
    }

    fn round_to_3_digit(&self) -> f64 {
        (*self * 1000.0).round() / 1000.0
    }

    fn round_to_4_digit(&self) -> f64 {
        (*self * 10000.0).round() / 10000.0
    }
}

pub fn min_max(x: f64, min_val: f64, max_val: f64) -> f64 {
    if x < min_val {
        min_val
    } else if x > max_val {
        max_val
    } else {
        x
    }
}
