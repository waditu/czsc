use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn longer_terminal_digit_sequences_fail_compilation() {
    let dependencies = std::env::current_exe()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();
    let macro_library = std::fs::read_dir(&dependencies)
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .filter(|path| {
            path.file_name()
                .unwrap()
                .to_string_lossy()
                .starts_with("libczsc_signal_macros-")
                && path.extension().is_some_and(|extension| {
                    extension == "dylib" || extension == "so" || extension == "dll"
                })
        })
        .max_by_key(|path| path.metadata().unwrap().modified().unwrap())
        .expect("compiled proc-macro library");
    for (version, wrong_version) in [("230101", "99230101"), ("20221118", "9920221118")] {
        let source = format!(
            r#"
            use czsc_signal_macros::signal;
            struct CZSC;
            struct ParamView;
            struct TaCache;
            #[signal(category = "kline", name = "audit_V{version}",
                template = "{{freq}}_D1_KV{wrong_version}", opcode = "Audit", param_kind = "Audit")]
            fn audit_v{version}(_: &CZSC, _: &ParamView, _: &mut TaCache) {{}}
            "#
        );
        let mut child = Command::new(std::env::var_os("RUSTC").unwrap_or_else(|| "rustc".into()))
            .args([
                "--edition=2024",
                "--crate-type=lib",
                "--emit=metadata",
                "--extern",
            ])
            .arg(format!("czsc_signal_macros={}", macro_library.display()))
            .arg("-")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(source.as_bytes())
            .unwrap();
        let output = child.wait_with_output().unwrap();
        let diagnostics = String::from_utf8(output.stderr).unwrap();
        assert!(!output.status.success(), "{version}: {diagnostics}");
        assert!(
            diagnostics.contains("k3 的末尾完整连续数字串必须与注册版本完全相等"),
            "{version}: {diagnostics}"
        );
    }
}
