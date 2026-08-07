use log::{error, info};
use serde::Serialize;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{Emitter, Manager};
use tauri_plugin_updater::UpdaterExt;

#[derive(Clone, Serialize)]
pub struct OllamaStatus {
    pub healthy: bool,
    pub version: Option<String>,
    pub endpoint: String,
}

#[derive(Clone, Serialize)]
pub struct PullProgress {
    pub model_id: String,
    pub status: String,
    pub percentage: Option<u8>,
    pub total: Option<String>,
    pub completed: Option<String>,
}

#[derive(Clone, Serialize)]
pub struct WindowState {
    pub minimized: bool,
    pub maximized: bool,
    pub visible: bool,
}

/// Check Ollama status: is it installed? is the API reachable?
#[tauri::command]
fn check_ollama() -> Result<OllamaStatus, String> {
    let endpoint = "http://localhost:11434";

    // Check if Ollama binary exists on disk
    let mut installed = false;
    #[cfg(target_os = "macos")]
    {
        use std::process::Command;
        let output = Command::new("which")
            .arg("ollama")
            .output()
            .ok();
        if let Some(out) = output {
            installed = !out.stdout.is_empty();
        }
    }

    // Check if API is reachable
    let mut healthy = false;
    let mut version: Option<String> = None;

    match reqwest::blocking::get(&format!("{}/api/version", endpoint)) {
        Ok(resp) => {
            if resp.status().is_success() {
                healthy = true;
                if let Ok(body) = resp.text() {
                    if let Ok(obj) = serde_json::from_str::<serde_json::Value>(&body) {
                        if let Some(v) = obj.get("version").and_then(|v| v.as_str()) {
                            version = Some(v.to_string());
                        }
                    }
                }
            }
        }
        Err(e) => {
            info!("Ollama not reachable: {}", e);
        }
    }

    // If reachable but not healthy, try to start Ollama on macOS
    if !healthy && installed {
        #[cfg(target_os = "macos")]
        {
            std::process::Command::new("open")
                .arg("-a")
                .arg("Ollama")
                .spawn()
                .ok();
            std::thread::sleep(std::time::Duration::from_secs(3));

            if let Ok(resp) =
                reqwest::blocking::get(&format!("{}/api/version", endpoint))
            {
                if resp.status().is_success() {
                    healthy = true;
                    if let Ok(body) = resp.text() {
                        if let Ok(obj) =
                            serde_json::from_str::<serde_json::Value>(&body)
                        {
                            if let Some(v) = obj
                                .get("version")
                                .and_then(|v| v.as_str())
                            {
                                version = Some(v.to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(OllamaStatus {
        healthy,
        version,
        endpoint: endpoint.to_string(),
    })
}

/// Pull an Ollama model (blocking). Emits progress events to the frontend.
#[tauri::command]
fn pull_model(
    app_handle: tauri::AppHandle,
    model_id: String,
) -> Result<PullProgress, String> {
    let endpoint = "http://localhost:11434";

    if model_id.is_empty() {
        return Err("Model ID cannot be empty".to_string());
    }

    // Start pull (non-streaming — Ollama will do work in background)
    let payload = serde_json::json!({
        "name": model_id,
        "stream": false
    });

    let client = reqwest::blocking::Client::new();

    match client.post(&format!("{}/api/pull", endpoint)).json(&payload).send() {
        Ok(resp) => {
            if resp.status().is_success() {
                // Check if model already exists in the list
                if let Ok(tags_resp) =
                    reqwest::blocking::get(&format!("{}/api/tags", endpoint))
                {
                    if tags_resp.status().is_success() {
                        if let Ok(tags_body) = tags_resp.text() {
                            if let Ok(tags_obj) =
                                serde_json::from_str::<serde_json::Value>(&tags_body)
                            {
                                if let Some(models_arr) = tags_obj
                                    .get("models")
                                    .and_then(|m| m.as_array())
                                {
                                    let exists = models_arr.iter().any(|m| {
                                        m.get("name")
                                            .and_then(|n| n.as_str())
                                            .map(|s| s == model_id)
                                            .unwrap_or(false)
                                    });
                                    if exists {
                                        app_handle
                                            .emit(
                                                "ollama-pull-progress",
                                                PullProgress {
                                                    model_id: model_id.clone(),
                                                    status: "complete".to_string(),
                                                    percentage: Some(100),
                                                    total: None,
                                                    completed: None,
                                                },
                                            )
                                            .ok();
                                    } else {
                                        app_handle
                                            .emit(
                                                "ollama-pull-progress",
                                                PullProgress {
                                                    model_id: model_id.clone(),
                                                    status: "pulling".to_string(),
                                                    percentage: Some(0),
                                                    total: None,
                                                    completed: None,
                                                },
                                            )
                                            .ok();
                                    }
                                }
                            }
                        }
                    }
                }

                Ok(PullProgress {
                    model_id,
                    status: "started".to_string(),
                    percentage: Some(0),
                    total: None,
                    completed: None,
                })
            } else {
                let status_text = resp.status().to_string();
                error!("Pull failed: {}", status_text);
                Err(format!("Pull failed: {}", status_text))
            }
        }
        Err(e) => Err(format!("Failed to start pull: {}", e)),
    }
}

/// Minimize the main window.
#[tauri::command]
fn minimize_window(app_handle: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        window.minimize().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Maximize or un-maximize the main window.
#[tauri::command]
fn maximize_window(app_handle: tauri::AppHandle) -> Result<WindowState, String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        let was_max = window.is_maximized().unwrap_or(false);
        if was_max {
            window.unmaximize().ok();
        } else {
            window.maximize().ok();
        }
        Ok(WindowState {
            minimized: window.is_minimized().unwrap_or(false),
            maximized: !was_max,
            visible: window.is_visible().unwrap_or(true),
        })
    } else {
        Err("Main window not found".to_string())
    }
}

/// Close (hide) the main window — does NOT quit the app.
#[tauri::command]
fn close_window(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        window.hide().ok();
    }
}

/// Quit the application entirely.
#[tauri::command]
fn quit_app(app_handle: tauri::AppHandle) {
    app_handle.exit(0);
}

/// Show the app window.
#[tauri::command]
fn show_window(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        window.show().ok();
        window.set_focus().ok();
    }
}

/// Hide the app window.
#[tauri::command]
fn hide_window(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        window.hide().ok();
    }
}

/// Get current window state.
#[tauri::command]
fn get_window_state(app_handle: tauri::AppHandle) -> Result<WindowState, String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        Ok(WindowState {
            minimized: window.is_minimized().unwrap_or(false),
            maximized: window.is_maximized().unwrap_or(false),
            visible: window.is_visible().unwrap_or(true),
        })
    } else {
        Err("Main window not found".to_string())
    }
}

/// Navigate the frontend page.
#[tauri::command]
fn navigate(app_handle: tauri::AppHandle, path: String) -> Result<(), String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        if let Ok(base) = window.url() {
            let new_url = format!(
                "{}/{}",
                base.as_str().trim_end_matches('/'),
                path.trim_start_matches('/')
            );
            let parsed = tauri::Url::parse(&new_url).map_err(|e| e.to_string())?;
            window.navigate(parsed).ok();
        }
    }
    Ok(())
}

/// Check for Tauri updates.
#[tauri::command]
async fn check_updates(app_handle: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let updater = app_handle
        .updater_builder()
        .build()
        .map_err(|e| e.to_string())?;
    let update = updater.check().await.map_err(|e| e.to_string())?;

    if let Some(update) = update {
        Ok(serde_json::json!({
            "update_available": true,
            "version": update.version,
            "date": update.date.map(|d| d.to_string()),
            "body": update.body,
            "signature": update.signature,
        }))
    } else {
        Ok(serde_json::json!({
            "update_available": false,
        }))
    }
}

/// Install a downloaded update.
#[tauri::command]
async fn install_update(app_handle: tauri::AppHandle) -> Result<(), String> {
    let updater = app_handle
        .updater_builder()
        .build()
        .map_err(|e| e.to_string())?;
    let update = updater
        .check()
        .await
        .map_err(|e| e.to_string())?
        .ok_or_else(|| "No update available".to_string())?;
    update
        .download_and_install(|_, _| {}, || {})
        .await
        .map_err(|e| e.to_string())
}

/// Parse the `models` array from an Ollama `/api/tags` response body into
/// a list of model names. Pure function — unit-testable without a network call.
fn parse_ollama_models(body: &str) -> Vec<String> {
    let Ok(obj) = serde_json::from_str::<serde_json::Value>(body) else {
        return Vec::new();
    };
    obj.get("models")
        .and_then(|m| m.as_array())
        .map(|models| {
            models
                .iter()
                .filter_map(|m| m.get("name").and_then(|n| n.as_str()))
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or_default()
}

/// Get list of running Ollama models.
#[tauri::command]
fn get_ollama_models() -> Result<Vec<String>, String> {
    let endpoint = "http://localhost:11434";

    match reqwest::blocking::get(&format!("{}/api/tags", endpoint)) {
        Ok(resp) => {
            if resp.status().is_success() {
                if let Ok(body) = resp.text() {
                    return Ok(parse_ollama_models(&body));
                }
            }
            Ok(Vec::new())
        }
        Err(e) => {
            error!("Failed to get models: {}", e);
            Err(format!("Ollama not reachable: {}", e))
        }
    }
}

/// Open native file picker; returns the chosen path (or None if cancelled).
#[tauri::command]
fn open_file_picker(app: tauri::AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;

    let picked = app
        .dialog()
        .file()
        .set_title("Datei auswählen")
        .blocking_pick_file();

    Ok(picked.map(|fp| fp.to_string()))
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().level(log::LevelFilter::Info).build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // macOS: Enable custom (overlay) title bar
            #[cfg(target_os = "macos")]
            {
                if let Some(window) = app.get_webview_window("main") {
                    window
                        .set_title_bar_style(tauri::TitleBarStyle::Overlay)
                        .ok();
                }
            }

            // Build system tray
            create_tray(app)?;

            // Mark onboarding as complete after first run
            let onboarding_dir = app.path().app_data_dir()?;
            let completed_flag = onboarding_dir.join(".miminox-onboarding-done");
            if !completed_flag.exists() {
                std::fs::create_dir_all(&onboarding_dir).ok();
                std::fs::write(&completed_flag, "done").ok();
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            check_ollama,
            pull_model,
            minimize_window,
            maximize_window,
            close_window,
            show_window,
            hide_window,
            quit_app,
            get_window_state,
            navigate,
            check_updates,
            install_update,
            get_ollama_models,
            open_file_picker,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn create_tray(app: &tauri::App) -> Result<(), String> {
    let show_item = MenuItem::with_id(app, "show", "Show MiMi Nox", true, None::<&str>)
        .map_err(|e| format!("Failed to create show menu item: {}", e))?;

    let hide_item = MenuItem::with_id(app, "hide", "Hide MiMi Nox", true, None::<&str>)
        .map_err(|e| format!("Failed to create hide menu item: {}", e))?;

    let new_session_item = MenuItem::with_id(app, "new-session", "New Session", true, None::<&str>)
        .map_err(|e| format!("Failed to create new session menu item: {}", e))?;

    let quit_item = MenuItem::with_id(app, "quit", "Quit MiMi Nox", true, None::<&str>)
        .map_err(|e| format!("Failed to create quit menu item: {}", e))?;

    let menu = Menu::with_items(app, &[&show_item, &hide_item, &new_session_item, &quit_item])
        .map_err(|e| format!("Failed to create tray menu: {}", e))?;

    let _tray = TrayIconBuilder::new()
        .menu(&menu)
        .show_menu_on_left_click(true)
        .tooltip("MiMi Nox — Local AI")
        .icon(app.default_window_icon().unwrap().clone())
        .on_menu_event(move |app, event| {
            match event.id().as_ref() {
                "show" => {
                    if let Some(window) = app.get_webview_window("main") {
                        window.show().ok();
                        window.set_focus().ok();
                    }
                }
                "hide" => {
                    if let Some(window) = app.get_webview_window("main") {
                        window.hide().ok();
                    }
                }
                "quit" => {
                    app.exit(0);
                }
                "new-session" => {
                    if let Some(window) = app.get_webview_window("main") {
                        window.show().ok();
                        window.set_focus().ok();
                        window.emit("create-session", ()).ok();
                    }
                }
                _ => {}
            }
        })
        .build(app)
        .map_err(|e| format!("Failed to create tray: {}", e))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::parse_ollama_models;

    #[test]
    fn parses_model_names_from_tags_response() {
        let body = r#"{"models":[{"name":"gemma4:e4b"},{"name":"qwen3-vl:4b"},{"name":"nomic-embed-text"}]}"#;
        let names = parse_ollama_models(body);
        assert_eq!(names, vec!["gemma4:e4b", "qwen3-vl:4b", "nomic-embed-text"]);
    }

    #[test]
    fn returns_empty_when_no_models_key() {
        assert_eq!(parse_ollama_models(r#"{"foo":"bar"}"#), Vec::<String>::new());
    }

    #[test]
    fn returns_empty_on_invalid_json() {
        assert_eq!(parse_ollama_models("not json"), Vec::<String>::new());
    }

    #[test]
    fn skips_models_without_name_field() {
        let body = r#"{"models":[{"name":"a"},{"size":123},{"name":"b"}]}"#;
        assert_eq!(parse_ollama_models(body), vec!["a", "b"]);
    }
}