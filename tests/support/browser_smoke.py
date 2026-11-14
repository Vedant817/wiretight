"""Real-browser authorization, passkey, CSRF and cancellation tests; no provider I/O."""

# ruff: noqa: E501, RUF001

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from tests.support.browser_fixture import server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    with server(), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://localhost:8766/")
            expect(page.get_by_role("heading", name="Sign in to your workspace")).to_be_visible()
            expect(page.locator("#readiness")).to_contain_text("Execution unavailable")

            def login(index):
                page.get_by_label("Email", exact=True).fill(f"browser{index}@example.test")
                page.get_by_label("Password", exact=True).fill(
                    f"browser-test-password-{index}-long"
                )
                page.get_by_role("button", name="Sign in", exact=True).click()
                expect(page.locator("#workspace")).to_be_visible()
                expect(page.locator("#approval-list .card")).to_have_count(1)

            login(3)
            expect(page.get_by_role("button", name="Approve with passkey")).to_have_count(0)
            expect(page.get_by_role("button", name="Request execution")).to_have_count(0)
            expect(page.get_by_role("button", name="Prepare approval")).to_be_hidden()
            for endpoint in ("options", "execute", "quote", "cancel"):
                status = page.evaluate(
                    """async endpoint => {
                    const csrf = document.cookie.split('; ').find(c => c.startsWith('wt_csrf=')).slice(8);
                    return (await fetch('/api/approvals/browser-approval/' + endpoint, {
                        method:'POST', headers:{'x-csrf-token':csrf,'content-type':'application/json'},
                        ...(endpoint === 'cancel' ? {body:JSON.stringify({reason:'unauthorized test'})} : {})
                    })).status;
                }""",
                    endpoint,
                )
                assert status == 403
            print(
                "PASS: ops UI hides money controls; direct requests to every packet action are refused"
            )
            page.screenshot(path=str(output / "ops-workspace.png"), full_page=True)
            page.get_by_role("button", name="Sign out").click()
            login(1)
            cdp = context.new_cdp_session(page)
            cdp.send("WebAuthn.enable")
            authenticator = cdp.send(
                "WebAuthn.addVirtualAuthenticator",
                {
                    "options": {
                        "protocol": "ctap2",
                        "transport": "internal",
                        "hasResidentKey": True,
                        "hasUserVerification": True,
                        "isUserVerified": True,
                        "automaticPresenceSimulation": True,
                    }
                },
            )["authenticatorId"]
            page.get_by_role("button", name="Register this account’s passkey").click()
            expect(page.locator("#notice")).to_contain_text("Passkey registered")
            for endpoint in ("options", "execute"):
                status = page.evaluate(
                    """async endpoint => (await fetch(
                    '/api/approvals/browser-approval/' + endpoint, {method:'POST'})).status""",
                    endpoint,
                )
                assert status == 401
            # Sign in again after the deliberate rejected CSRF request.
            page.reload()
            expect(page.locator("#workspace")).to_be_visible()
            page.get_by_role("button", name="Approve with passkey").click()
            expect(page.locator("#notice")).to_contain_text("Approval signature recorded")
            expect(page.locator("#approval-list")).to_contain_text("1 / 2")
            print(
                "PASS: browser passkey registration and approval verify on the server; CSRF is refused"
            )
            page.get_by_role("button", name="Sign out").click()
            login(2)
            page.get_by_role("button", name="Register this account’s passkey").click()
            expect(page.locator("#notice")).to_contain_text("Passkey registered")
            # Obtain a real browser assertion in tab A but hold its finish request.
            page.evaluate(r"""async () => {
                const csrf=document.cookie.split('; ').find(c=>c.startsWith('wt_csrf=')).slice(8);
                const prompt=await (await fetch('/api/approvals/browser-approval/options',{
                    method:'POST',headers:{'x-csrf-token':csrf}})).json();
                const decode=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+
                    '='.repeat((4-s.length%4)%4)), c=>c.charCodeAt(0));
                const encode=b=>btoa(String.fromCharCode(...new Uint8Array(b)))
                    .replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
                const pk=prompt.publicKey;pk.challenge=decode(pk.challenge);
                pk.allowCredentials.forEach(c=>c.id=decode(c.id));
                const credential=await navigator.credentials.get({publicKey:pk});
                window.pendingProof={ceremony_id:prompt.ceremony_id,credential:{
                    id:credential.id,rawId:encode(credential.rawId),type:credential.type,
                    response:{clientDataJSON:encode(credential.response.clientDataJSON),
                        authenticatorData:encode(credential.response.authenticatorData),
                        signature:encode(credential.response.signature)}}};
            }""")
            other_tab = context.new_page()
            other_tab.goto("http://localhost:8766/")
            expect(other_tab.locator("#workspace")).to_be_visible()
            other_tab.get_by_role("button", name="Cancel approval", exact=True).click()
            other_tab.get_by_label("Reason", exact=True).fill("Browser cancellation in another tab")
            other_tab.locator("#cancel-form").get_by_role(
                "button", name="Cancel approval", exact=True
            ).click()
            expect(other_tab.locator("#approval-list")).to_contain_text("VOID")
            stale_status = page.evaluate("""async () => {
                const csrf=document.cookie.split('; ').find(c=>c.startsWith('wt_csrf=')).slice(8);
                return (await fetch('/api/passkeys/finish',{method:'POST',headers:{
                    'x-csrf-token':csrf,'content-type':'application/json'},
                    body:JSON.stringify(window.pendingProof)})).status;
            }""")
            assert stale_status == 409
            other_tab.close()
            page.reload()
            expect(page.locator("#approval-list")).to_contain_text("VOID")
            expect(page.get_by_role("button", name="Approve with passkey")).to_have_count(0)
            print("PASS: genuine browser assertion from tab A is refused after tab B cancels")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "mobile-workspace.png"), full_page=True)
            assert errors == [], errors
            cdp.send("WebAuthn.removeVirtualAuthenticator", {"authenticatorId": authenticator})
            print(
                "PASS: cancellation updates the approval UI; mobile layout fits; no browser script errors"
            )
            (output / "browser-result.json").write_text(
                json.dumps(
                    {
                        "provider_calls": "none; keys absent",
                        "script_errors": errors,
                        "passkeys": "Chromium virtual authenticator; not physical-device acceptance",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        finally:
            browser.close()


if __name__ == "__main__":
    main()
