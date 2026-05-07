#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CandidateChunk {
    pub start: usize,
    pub end: usize,
}

pub fn build_candidate_chunks(total: usize, chunk_size: usize) -> Vec<CandidateChunk> {
    if total == 0 {
        return Vec::new();
    }
    let step = chunk_size.max(1);
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < total {
        let end = (i + step).min(total);
        out.push(CandidateChunk { start: i, end });
        i = end;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::build_candidate_chunks;

    #[test]
    fn chunk_split_is_deterministic() {
        let c = build_candidate_chunks(10, 3);
        assert_eq!(c.len(), 4);
        assert_eq!(c[0].start, 0);
        assert_eq!(c[0].end, 3);
        assert_eq!(c[3].start, 9);
        assert_eq!(c[3].end, 10);
    }
}
