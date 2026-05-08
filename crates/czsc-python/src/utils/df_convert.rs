use crate::errors::PythonError;
use polars::prelude::*;
use std::io::Cursor;

pub fn pyarrow_to_df(data: &[u8]) -> Result<DataFrame, PythonError> {
    let cursor = Cursor::new(data);
    let df = IpcReader::new(cursor).finish().map_err(PythonError::from)?;
    Ok(df)
}

/// 将DataFrame转换为字节数组
pub fn df_to_pyarrow(dataframe: &mut DataFrame) -> Result<Vec<u8>, PythonError> {
    let mut buffer = Cursor::new(Vec::new());
    IpcWriter::new(&mut buffer).finish(dataframe)?;
    Ok(buffer.into_inner())
}
