#![cfg(feature = "python")]

use czsc_core::objects::{direction::Direction, freq::Freq, market::Market};
use pyo3::{prelude::*, types::PyDict};
use std::{ffi::CString, fmt::Debug};
use strum::IntoEnumIterator;

fn assert_copy_extraction<T>(py: Python<'_>, expected: T, object: Py<T>)
where
    T: pyo3::PyClass + Copy + PartialEq + Debug + for<'a, 'py> FromPyObject<'a, 'py>,
{
    for _ in 0..2 {
        let extracted = object
            .bind(py)
            .as_any()
            .extract::<T>()
            .unwrap_or_else(|_| panic!("extract {expected:?}"));
        assert_eq!(extracted, expected);
    }
    assert_eq!(*object.borrow(py), expected);
    assert!(py.None().bind(py).extract::<T>().is_err());
    assert!("invalid".into_pyobject(py).unwrap().extract::<T>().is_err());
}

#[test]
fn all_python_enum_variants_extract_by_value_without_consuming_object() {
    Python::initialize();
    Python::attach(|py| {
        for direction in [Direction::Up, Direction::Down] {
            assert_copy_extraction(py, direction, Py::new(py, direction).unwrap());
        }
        for freq in Freq::iter() {
            assert_copy_extraction(py, freq, Py::new(py, freq).unwrap());
        }
        for market in [Market::AShare, Market::Futures, Market::Default] {
            assert_copy_extraction(py, market, Py::new(py, market).unwrap());
        }
        let direction = Py::new(py, Direction::Up).unwrap();
        assert!(direction.bind(py).as_any().extract::<Freq>().is_err());
        assert!(direction.bind(py).as_any().extract::<Market>().is_err());
    });
}

#[test]
fn python_constructors_and_equality_keep_extraction_contract() {
    Python::initialize();
    Python::attach(|py| {
        let locals = PyDict::new(py);
        locals
            .set_item("Direction", py.get_type::<Direction>())
            .unwrap();
        locals.set_item("Freq", py.get_type::<Freq>()).unwrap();
        locals.set_item("Market", py.get_type::<Market>()).unwrap();
        let script = CString::new(
            "direction = Direction('Up')\nassert direction == Direction.Up\nassert direction != Direction.Down\n\
             freq = Freq('60分钟')\nassert freq == Freq.F60\nassert freq != Freq.F1\n\
             market = Market('A股')\nassert market == Market.AShare\nassert market != Market.Futures\n",
        ).unwrap();
        py.run(&script, Some(&locals), Some(&locals)).unwrap();
        assert_eq!(
            locals
                .get_item("direction")
                .unwrap()
                .unwrap()
                .extract::<Direction>()
                .unwrap(),
            Direction::Up
        );
        assert_eq!(
            locals
                .get_item("freq")
                .unwrap()
                .unwrap()
                .extract::<Freq>()
                .unwrap(),
            Freq::F60
        );
        assert_eq!(
            locals
                .get_item("market")
                .unwrap()
                .unwrap()
                .extract::<Market>()
                .unwrap(),
            Market::AShare
        );
    });
}
