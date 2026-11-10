"""Read-only browser checks for the deployed Phase 10 dashboard and 3D scene.

All non-same-origin requests are blocked by default. This keeps the audit from
contacting ad networks, analytics vendors, or unrelated third-party services.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, (parsed.hostname or "").lower(), parsed.port or default_port


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    if parsed.port:
        host += f":{parsed.port}"
    return f"{parsed.scheme}://{host}{parsed.path[:220]}"


def _camera_yaw_degrees(state: dict) -> float:
    camera = state["camera"]
    target = state["target"]
    return math.degrees(math.atan2(camera["x"] - target["x"], camera["z"] - target["z"]))


def _angle_delta_degrees(after: float, before: float) -> float:
    return (after - before + 180.0) % 360.0 - 180.0


async def _wait_for_camera(page, preset: str, timeout_ms: int = 12000) -> None:
    expected = {
        "panorama": {"zone": "command", "radius": 37.0, "target": [0.0, 2.6, 0.0]},
        "agents": {"zone": "agents", "radius": 12.0, "target": [-8.2, 2.9, -7.4]},
        "ads": {"zone": "ads", "radius": 12.2, "target": [8.2, 2.9, -7.4]},
        "products": {"zone": "products", "radius": 14.5, "target": [-9.1, 2.6, 6.7]},
        "live": {"zone": "live", "radius": 10.4, "target": [0.0, 3.8, 9.1]},
        "revenue": {"zone": "revenue", "radius": 12.2, "target": [9.1, 2.6, 6.7]},
    }[preset]
    await page.wait_for_function("""expected => {
      const api = window.__AUTOProfitCommandCenter;
      if (!api || !api.getDebugState) return false;
      const s = api.getDebugState();
      const targetError = Math.hypot(s.target.x-expected.target[0],s.target.y-expected.target[1],s.target.z-expected.target[2]);
      const radiusNear = expected.zone === 'command' ? s.cameraRadius >= expected.radius-3.5 : s.cameraRadius < 18;
      return s.selectedZone === expected.zone && targetError < 3.2 && radiusNear;
    }""", arg=expected, timeout=timeout_ms)


async def _project_world(page, world: list[float]) -> dict | None:
    return await page.evaluate("""world => {
      const api = window.__AUTOProfitCommandCenter;
      const canvas = document.querySelector('#apSceneCanvas');
      if (!api || !canvas) return null;
      const s = api.getDebugState();
      const eye = [s.camera.x, s.camera.y, s.camera.z];
      const target = [s.target.x, s.target.y, s.target.z];
      const norm = v => { const l = Math.hypot(...v); return v.map(x => x / l); };
      const dot = (a,b) => a.reduce((sum,x,i) => sum + x*b[i], 0);
      const cross = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
      const forward = norm(target.map((x,i) => x-eye[i]));
      const right = norm(cross(forward, [0,1,0]));
      const up = cross(right, forward);
      const delta = world.map((x,i) => x-eye[i]);
      const depth = dot(delta, forward);
      if (depth <= 0.01) return null;
      const aspect = canvas.clientWidth / Math.max(1, canvas.clientHeight);
      const halfHeight = Math.tan(40 * Math.PI / 360) * depth;
      const ndcX = dot(delta, right) / (halfHeight * aspect);
      const ndcY = dot(delta, up) / halfHeight;
      const rect = canvas.getBoundingClientRect();
      return {
        x: rect.left + (ndcX + 1) * rect.width / 2,
        y: rect.top + (1 - ndcY) * rect.height / 2,
        depth, ndcX, ndcY,
        inside: Math.abs(ndcX) <= 0.96 && Math.abs(ndcY) <= 0.84
      };
    }""", world)


async def _check_view(browser, url: str, label: str, width: int, height: int,
                      output_dir: Path, *, run_interactions: bool,
                      navigation_timeout_ms: int) -> dict:
    context = await browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1,
        is_mobile=label == "mobile",
        has_touch=label == "mobile",
        reduced_motion="reduce" if label == "mobile" else "no-preference",
    )
    page = await context.new_page()
    same_origin = _origin(url)
    evidence = {
        "viewport": {"width": width, "height": height, "device": label},
        "console_errors": [],
        "page_errors": [],
        "failed_requests": [],
        "http_errors": [],
        "blocked_external_requests": [],
        "checks": {},
    }

    page.on("console", lambda message: evidence["console_errors"].append(message.text[:500])
            if message.type == "error" else None)
    page.on("pageerror", lambda error: evidence["page_errors"].append(str(error)[:500]))
    page.on("requestfailed", lambda request: evidence["failed_requests"].append(
        {"url": _safe_url(request.url), "error": (request.failure or "unknown")[:200]}))

    async def same_origin_only(route):
        target = _origin(route.request.url)
        if target != same_origin:
            evidence["blocked_external_requests"].append(_safe_url(route.request.url))
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    await page.route("**/*", same_origin_only)
    page.on("response", lambda response: evidence["http_errors"].append(
        {"status": response.status, "url": _safe_url(response.url)})
            if response.status >= 400 and _origin(response.url) == same_origin else None)

    started = time.monotonic()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=navigation_timeout_ms)
        evidence["http_status"] = response.status if response else None
        await page.wait_for_timeout(1400)
        evidence["checks"]["dashboard_loaded"] = bool(response and response.ok)
        evidence["api_smoke"] = await page.evaluate("""async () => {
          const checks = {};
          for (const [name,path] of [['health','/api/health'],['readiness','/api/ready'],
                                     ['anonymous_admin','/api/optimization/admin/proposals'],
                                     ['anonymous_cash_admin','/api/cash/admin/orders'],
                                     ['cash_catalog','/api/cash/catalog']]) {
            try {
              const response = await fetch(path,{method:'GET',credentials:'omit',cache:'no-store'});
              checks[name] = {status:response.status};
              if (name === 'cash_catalog' && response.ok) {
                const body = await response.json();
                checks[name].payment_configured = body.payment_configured === true;
              }
            } catch (_) { checks[name] = {status:null}; }
          }
          return checks;
        }""")
        evidence["checks"]["health_api"] = evidence["api_smoke"]["health"]["status"] == 200
        evidence["checks"]["readiness_api"] = evidence["api_smoke"]["readiness"]["status"] == 200
        evidence["checks"]["anonymous_admin_denied"] = evidence["api_smoke"]["anonymous_admin"]["status"] in (401, 403, 503)
        evidence["checks"]["anonymous_cash_admin_denied"] = evidence["api_smoke"]["anonymous_cash_admin"]["status"] in (401, 403, 503)
        evidence["checks"]["live_payment_destination_disabled"] = (
            evidence["api_smoke"]["cash_catalog"]["status"] == 200
            and evidence["api_smoke"]["cash_catalog"].get("payment_configured") is False
        )
        await page.screenshot(path=str(output_dir / f"{label}-dashboard.png"), full_page=False)

        command_center = page.locator("#apCommandCenter")
        evidence["checks"]["command_center_present"] = await command_center.count() == 1
        if await command_center.count():
            await command_center.scroll_into_view_if_needed(timeout=8000)
            await page.wait_for_timeout(2500)
            canvas = page.locator("#apSceneCanvas")
            evidence["checks"]["scene_canvas_present"] = await canvas.count() == 1
            state = await page.evaluate("""() => {
              const api = window.__AUTOProfitCommandCenter;
              if (!api || typeof api.getDebugState !== 'function') return null;
              const state = api.getDebugState();
              const canvas = document.querySelector('#apSceneCanvas');
              let gl = canvas && (canvas.getContext('webgl2') || canvas.getContext('webgl'));
              const debugRenderer = gl && gl.getExtension('WEBGL_debug_renderer_info');
              return {
                state,
                webgl: gl ? {
                  contextLost: gl.isContextLost(),
                  error: gl.getError(),
                  maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                  renderer: debugRenderer ? gl.getParameter(debugRenderer.UNMASKED_RENDERER_WEBGL) : 'not exposed'
                } : null,
                statusText: document.querySelector('#apSceneDataState')?.textContent || null
              };
            }""")
            evidence["scene_initial"] = state
            evidence["checks"]["three_scene_initialized"] = bool(
                state and state.get("state", {}).get("render", {}).get("hasRenderedFrame")
                and state.get("webgl") and not state["webgl"]["contextLost"]
            )
            evidence["checks"]["webgl_context_healthy"] = bool(
                state and state.get("webgl") and not state["webgl"]["contextLost"]
                and state["webgl"]["error"] == 0
            )
            await command_center.screenshot(path=str(output_dir / f"{label}-scene-panorama.png"))

            if run_interactions and evidence["checks"]["three_scene_initialized"]:
                bounds = await canvas.bounding_box()
                before = await page.evaluate("""() => {
                  const s = window.__AUTOProfitCommandCenter.getDebugState();
                  return {camera:s.camera,target:s.target};
                }""")
                yaw_before = _camera_yaw_degrees(before)
                if bounds:
                    x0, y0 = bounds["x"] + bounds["width"] * 0.5, bounds["y"] + bounds["height"] * 0.5
                    await page.mouse.move(x0, y0)
                    await page.mouse.down()
                    await page.mouse.move(x0 + 262, y0, steps=12)
                    await page.mouse.up()
                    await page.wait_for_timeout(350)
                    after90 = await page.evaluate("""() => {
                      const s = window.__AUTOProfitCommandCenter.getDebugState();
                      return {camera:s.camera,target:s.target};
                    }""")
                    yaw_after90 = _camera_yaw_degrees(after90)
                    delta90 = _angle_delta_degrees(yaw_after90, yaw_before)
                    evidence["camera_rotation_degrees"] = {"initial_yaw": yaw_before, "after_first_drag": yaw_after90,
                                                            "first_delta": delta90}
                    evidence["checks"]["camera_rotate_90"] = 85 <= abs(delta90) <= 95
                    await command_center.screenshot(path=str(output_dir / f"{label}-scene-rotate-90.png"))

                    await page.mouse.move(x0, y0)
                    await page.mouse.down()
                    await page.mouse.move(x0 + 262, y0, steps=12)
                    await page.mouse.up()
                    await page.wait_for_timeout(350)
                    after180 = await page.evaluate("""() => {
                      const s = window.__AUTOProfitCommandCenter.getDebugState();
                      return {camera:s.camera,target:s.target};
                    }""")
                    yaw_after180 = _camera_yaw_degrees(after180)
                    delta_to_back = _angle_delta_degrees(yaw_after180, yaw_after90)
                    delta_from_start = _angle_delta_degrees(yaw_after180, yaw_before)
                    evidence["camera_rotation_degrees"].update({"after_second_drag": yaw_after180,
                                                                "second_delta": delta_to_back,
                                                                "total_from_start": delta_from_start})
                    evidence["checks"]["camera_rotate_180"] = (
                        85 <= abs(delta_to_back) <= 95 and abs(abs(delta_from_start) - 180) <= 10
                    )
                    await command_center.screenshot(path=str(output_dir / f"{label}-scene-rotate-180.png"))

                    radius_before_zoom = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState().cameraRadius")
                    await page.mouse.move(x0, y0)
                    await page.mouse.wheel(0, -520)
                    await page.wait_for_timeout(300)
                    radius_after_zoom = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState().cameraRadius")
                    evidence["zoom"] = {"before_radius": radius_before_zoom, "after_radius": radius_after_zoom}
                    evidence["checks"]["zoom_in"] = radius_after_zoom < radius_before_zoom

                preset_results = {}
                for preset in ("agents", "ads", "products", "live", "revenue", "panorama"):
                    button = page.locator(f"[data-ap-tab='{preset}']")
                    if await button.count():
                        await button.click()
                        settled = True
                        try:
                            await _wait_for_camera(page, preset)
                        except Exception:
                            settled = False
                        debug = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState()")
                        preset_results[preset] = {
                            "selected_zone": debug.get("selectedZone"),
                            "selected_object_id": debug.get("selectedObjectId"),
                            "camera_radius": debug.get("cameraRadius"),
                            "camera_near_target": settled,
                        }
                        if preset in ("agents", "ads", "products"):
                            await command_center.screenshot(path=str(output_dir / f"{label}-scene-{preset}.png"))
                evidence["camera_presets"] = preset_results
                evidence["checks"]["camera_presets"] = all(
                    preset_results.get(key, {}).get("selected_zone") == expected
                    and preset_results.get(key, {}).get("camera_near_target") is True
                    for key, expected in (("agents", "agents"), ("ads", "ads"),
                                          ("products", "products"), ("live", "live"),
                                          ("revenue", "revenue"), ("panorama", "command"))
                )

                await page.locator("[data-ap-tab='ads']").click()
                await _wait_for_camera(page, "ads")
                ad_state = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState()")
                ad_target = next((item for item in ad_state.get("landmarks", [])
                                  if item.get("objectId") == "ad-network"
                                  and item.get("screenPosition", {}).get("inView")), None)
                box = await canvas.bounding_box()
                ad_point = ad_target.get("screenPosition") if ad_target else None
                if ad_point and box and box["x"] < ad_point["x"] < box["x"] + box["width"] and box["y"] < ad_point["y"] < box["y"] + box["height"]:
                    await page.mouse.click(ad_point["x"], ad_point["y"])
                    await page.wait_for_timeout(300)
                    clicked = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState()")
                    evidence["ad_network_click"] = {
                        "target_object_id": ad_target["objectId"],
                        "target_name": ad_target["name"],
                        "assignment_status": ad_target.get("assignmentStatus"),
                        "screen_position": ad_point,
                        "selected_object_id": clicked.get("selectedObjectId"),
                        "selected_zone": clicked.get("selectedZone"),
                    }
                    evidence["checks"]["ad_network_object_click"] = clicked.get("selectedZone") == "ads" and clicked.get("selectedObjectId") == "ad-network"
                else:
                    evidence["checks"]["ad_network_object_click"] = False
                    evidence["ad_network_click"] = {"reason": "no visible, pickable Ad Network landmark", "screen_position": ad_point}

                await page.locator("[data-ap-tab='agents']").click()
                agents_near_target = True
                try:
                    await _wait_for_camera(page, "agents")
                except Exception:
                    agents_near_target = False
                agent_state = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState()")
                evidence["checks"]["agents_camera_near_target"] = agents_near_target
                box = await canvas.bounding_box()
                workstation_result = None
                workstation_pass = False
                for workstation in agent_state.get("workstations", []):
                    world = workstation.get("worldPosition") or []
                    if len(world) != 3:
                        continue
                    point = await _project_world(page, [world[0], world[1] + 0.72, world[2] + 0.35])
                    if not point or not point["inside"] or not box or not (box["x"] < point["x"] < box["x"] + box["width"] and box["y"] < point["y"] < box["y"] + box["height"]):
                        continue
                    await page.mouse.click(point["x"], point["y"])
                    await page.wait_for_timeout(250)
                    clicked = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState()")
                    workstation_result = {
                        "target_object_id": workstation["objectId"],
                        "target_name": workstation["name"],
                        "assignment_status": workstation.get("assignmentStatus"),
                        "screen_position": point,
                        "selected_object_id": clicked.get("selectedObjectId"),
                        "highlighted_workstation_id": clicked.get("highlightedWorkstationId"),
                    }
                    if clicked.get("selectedObjectId") == workstation["objectId"] and clicked.get("highlightedWorkstationId") == workstation["objectId"]:
                        workstation_pass = True
                        break
                evidence["workstation_click"] = workstation_result or {"reason": "no workstation projects into the visible scene"}
                evidence["checks"]["workstation_object_click"] = workstation_pass

                await page.locator("[data-ap-action='reset-scene']").click()
                panorama_near_target = True
                try:
                    await _wait_for_camera(page, "panorama")
                except Exception:
                    panorama_near_target = False
                reset = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState()")
                evidence["checks"]["reset_to_panorama"] = panorama_near_target and reset.get("selectedZone") == "command" and reset.get("cameraRadius", 0) >= 18

                evidence["fps_probe"] = await page.evaluate("""async () => {
                  const api = window.__AUTOProfitCommandCenter;
                  const canvas = document.querySelector('#apSceneCanvas');
                  if (!api || !canvas) return null;
                  canvas.focus({preventScroll:true});
                  const before = api.getDebugState().render.frames;
                  const start = performance.now();
                  return await new Promise(resolve => {
                    function step(now) {
                      if (now - start >= 1500) {
                        const elapsed = now - start;
                        const state = api.getDebugState();
                        resolve({elapsed_ms:Math.round(elapsed), frame_delta:state.render.frames-before,
                          measured_fps:state.render.measuredFps,
                          sampled_fps:Math.round((state.render.frames-before)*1000/elapsed),
                          draw_calls:state.render.calls, triangles:state.render.triangles, memory:state.memory});
                        return;
                      }
                      canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
                      requestAnimationFrame(step);
                    }
                    requestAnimationFrame(step);
                  });
                }""")
                evidence["checks"]["fps_probe_rendered"] = bool(evidence["fps_probe"] and evidence["fps_probe"].get("frame_delta", 0) > 0)
                evidence["checks"]["fps_interactive_24_plus"] = bool(
                    evidence["fps_probe"] and evidence["fps_probe"].get("sampled_fps", 0) >= 24
                )
                evidence["render_stats"] = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState().render")
                evidence["renderer_memory"] = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState().memory")
                evidence["static_batching"] = await page.evaluate("window.__AUTOProfitCommandCenter.getDebugState().staticBatching")

                focused = page.locator("[data-ap-tab='agents']")
                await focused.focus()
                await focused.press("ArrowRight")
                await page.wait_for_timeout(150)
                evidence["checks"]["keyboard_camera_tabs"] = await page.evaluate(
                    "document.activeElement?.dataset?.apTab === 'ads' && document.activeElement?.getAttribute('aria-selected') === 'true'"
                )
                await page.locator("[data-ap-action='reset-scene']").click()
                try:
                    await _wait_for_camera(page, "panorama")
                except Exception:
                    pass
        else:
            evidence["checks"].update({
                "scene_canvas_present": False,
                "three_scene_initialized": False,
                "webgl_context_healthy": False,
            })

        evidence["layout"] = await page.evaluate("""() => ({
          viewportWidth: innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
          reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
          webglStatus: document.querySelector('#apSceneDataState')?.textContent || null,
          sceneRect: (() => { const r = document.querySelector('#apCommandCenter')?.getBoundingClientRect(); return r ? {width:r.width,height:r.height,top:r.top,bottom:r.bottom} : null; })()
        })""")
        evidence["checks"]["no_horizontal_overflow"] = not evidence["layout"]["horizontalOverflow"]
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 2)
    except Exception as exc:
        evidence["exception"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        evidence["checks"]["browser_run_completed"] = False
    finally:
        await context.close()
    return evidence


async def run(url: str, output_dir: Path, *, software_rendering: bool = False,
              navigation_timeout_ms: int = 60000,
              browser_channel: str | None = None) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing evidence directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        launch_args = ["--enable-webgl", "--ignore-gpu-blocklist"]
        if software_rendering:
            launch_args.append("--use-angle=swiftshader")
        if browser_channel == "chrome" and not software_rendering:
            launch_args.extend(["--enable-gpu", "--disable-software-rasterizer", "--use-angle=d3d11"])
        browser = await playwright.chromium.launch(channel=browser_channel, headless=True, args=launch_args)
        results = []
        results.append(await _check_view(browser, url, "desktop-1920x1080", 1920, 1080, output_dir,
                                         run_interactions=True, navigation_timeout_ms=navigation_timeout_ms))
        results.append(await _check_view(browser, url, "desktop-1440x900", 1440, 900, output_dir,
                                         run_interactions=False, navigation_timeout_ms=navigation_timeout_ms))
        results.append(await _check_view(browser, url, "mobile-390x844", 390, 844, output_dir,
                                         run_interactions=False, navigation_timeout_ms=navigation_timeout_ms))
        await browser.close()
    report = {
        "url": url,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "policy": "same-origin requests only; all third-party network access blocked",
        "renderer_mode": "swiftshader" if software_rendering else "browser-default-gpu",
        "browser_channel": browser_channel or "playwright-chromium",
        "views": results,
    }
    path = output_dir / "browser-evidence.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence file: {path}")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="dashboard URL to inspect")
    parser.add_argument("--output-dir", required=True, type=Path, help="new or empty evidence folder")
    parser.add_argument("--software-rendering", action="store_true",
                        help="force SwiftShader; use only when hardware WebGL is unavailable")
    parser.add_argument("--browser-channel", choices=("chrome",),
                        help="use installed Chrome with hardware GPU flags when available")
    parser.add_argument("--navigation-timeout-ms", type=int, default=60000,
                        help="page navigation timeout for shader compilation and slow hosts (default: 60000)")
    args = parser.parse_args()
    if not 1000 <= args.navigation_timeout_ms <= 180000:
        parser.error("--navigation-timeout-ms must be between 1000 and 180000")
    report = asyncio.run(run(args.url, args.output_dir, software_rendering=args.software_rendering,
                             navigation_timeout_ms=args.navigation_timeout_ms,
                             browser_channel=args.browser_channel))
    print(json.dumps({
        "evidence": str(args.output_dir.resolve() / "browser-evidence.json"),
        "views": len(report["views"]),
        "exceptions": sum(bool(view.get("exception")) for view in report["views"]),
        "failed_checks": sum(value is False for view in report["views"] for value in view.get("checks", {}).values()),
    }, ensure_ascii=True))
    failed = any(view.get("exception") for view in report["views"]) or any(
        value is False for view in report["views"] for value in view.get("checks", {}).values()
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
