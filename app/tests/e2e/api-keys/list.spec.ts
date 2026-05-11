import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createApiKey, expireApiKey } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.describe("API Keys list - smoke", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createApiKey({ name: "smoke-key-1" });
    await createApiKey({ name: "smoke-key-2" });
  });

  test("AK-01 @smoke API キー一覧が表示される（key 値はマスクされている）", async ({
    page,
  }) => {
    await page.goto("/api-keys");

    const rows = page.getByTestId("api-key-row");
    await expect(rows).toHaveCount(2);

    const masks = page.getByTestId("api-key-masked");
    await expect(masks.first()).toBeVisible();
    // マスク済みは `*` または `•` を含むはず
    await expect(masks.first()).toContainText(/[*•]/);
  });
});

test.describe("API Keys list - create", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("AK-02 全 scope チェック + name 入力で作成 → 平文 key が表示される", async ({
    page,
  }) => {
    await page.goto("/api-keys");

    await page.getByTestId("api-key-create-button").click();

    await page.getByTestId("api-key-form-name").fill("AK-02 full scope");

    // read は初期 ON。残り write/delete/admin を ON にする。
    // checked が undefined のものもあるので setChecked で冪等に。
    for (const scope of ["read", "write", "delete", "admin"]) {
      const cb = page.getByTestId(`api-key-form-scope-${scope}`);
      await cb.click();
      // Radix Checkbox は data-state="checked|unchecked"。click でトグルしすぎないよう
      // checked になっていなければもう一度クリックして合わせる。
      const state = await cb.getAttribute("data-state");
      if (state !== "checked") {
        await cb.click();
      }
    }

    await page.getByTestId("api-key-form-submit").click();

    // 作成成功後は平文 key dialog が出る。
    const plaintext = page.getByTestId("api-key-plaintext");
    await expect(plaintext).toBeVisible();
    // 既定 prefix gb_live_ で始まる。
    await expect(plaintext).toHaveText(/^gb_/);
  });
});

test.describe("API Keys list - scopes", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("AK-03 scope=read のみで作成 → 一覧で read のみが付与されている", async ({
    page,
  }) => {
    await page.goto("/api-keys");

    await page.getByTestId("api-key-create-button").click();
    await page.getByTestId("api-key-form-name").fill("AK-03 read only");
    // read は既定で checked。他は触らない。
    await page.getByTestId("api-key-form-submit").click();

    // 平文 dialog を閉じる (Esc で OK)。
    await expect(page.getByTestId("api-key-plaintext")).toBeVisible();
    await page.keyboard.press("Escape");

    // 一覧の行に scopes=read だけが書かれている。
    const row = page.getByTestId("api-key-row").first();
    await expect(row).toHaveAttribute("data-key-scopes", "read");
  });
});

test.describe("API Keys list - clipboard copy", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("AK-04 作成直後の copy ボタンで clipboard に平文 key が入る", async ({
    page,
    context,
  }) => {
    // Chromium では clipboard-read / clipboard-write の両方を grant して
    // navigator.clipboard.writeText を動かす。
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);

    await page.goto("/api-keys");

    await page.getByTestId("api-key-create-button").click();
    await page.getByTestId("api-key-form-name").fill("AK-04 clipboard");
    await page.getByTestId("api-key-form-submit").click();

    const plaintext = page.getByTestId("api-key-plaintext");
    await expect(plaintext).toBeVisible();
    const keyValue = (await plaintext.textContent())?.trim() ?? "";
    expect(keyValue).toMatch(/^gb_/);

    await page.getByTestId("api-key-copy-button").click();

    // navigator.clipboard.readText の値が key と一致することを確認。
    const clipboard = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboard).toBe(keyValue);
  });
});

test.describe("API Keys list - revoke", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createApiKey({ name: "AK-05 target" });
  });

  test("AK-05 dropdown → revoke で status=revoked に変わる", async ({ page }) => {
    await page.goto("/api-keys");

    const row = page.getByTestId("api-key-row").first();
    await expect(row).toHaveAttribute("data-key-status", "active");

    // dropdown trigger は最後の Button (MoreHorizontal アイコン)。
    await row.getByRole("button").last().click();
    await page.getByTestId("api-key-revoke-menuitem").click();

    await page.getByTestId("api-key-revoke-reason").fill("E2E test revoke");
    await page.getByTestId("api-key-revoke-confirm").click();

    // status badge が「無効化済み」へ。dataset も更新される。
    await expect(row).toHaveAttribute("data-key-status", "revoked");
    await expect(row.getByText("無効化済み")).toBeVisible();
  });
});

test.describe("API Keys list - delete revoked", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("AK-06 revoked key を削除すると一覧から消える", async ({ page }) => {
    // factory で 1 件作る → UI で revoke → delete の順。
    await createApiKey({ name: "AK-06 target" });

    await page.goto("/api-keys");

    const rows = page.getByTestId("api-key-row");
    await expect(rows).toHaveCount(1);

    // revoke
    await rows.first().getByRole("button").last().click();
    await page.getByTestId("api-key-revoke-menuitem").click();
    await page.getByTestId("api-key-revoke-confirm").click();
    await expect(rows.first()).toHaveAttribute("data-key-status", "revoked");

    // delete
    await rows.first().getByRole("button").last().click();
    await page.getByTestId("api-key-delete-menuitem").click();
    await page.getByTestId("api-key-delete-confirm").click();

    await expect(rows).toHaveCount(0);
  });
});

test.describe("API Keys list - expired status", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    // factory で作成 → test_helpers で expires_at を過去日時に書き換える。
    // `ApiKeyCreate.expires_in_days` は 1..365 の正の範囲しか許容しないため、
    // 直接 SQL で expires_at を埋めるしか手段がない (AK-07 解説)。
    const created = await createApiKey({ name: "expired-key" });
    await expireApiKey({ keyId: created.id, minutesAgo: 60 });
  });

  test("AK-07 期限切れ key の status 表示", async ({ page }) => {
    await page.goto("/api-keys");

    const row = page.getByTestId("api-key-row").first();
    await expect(row).toBeVisible({ timeout: 10_000 });
    // UI は `data-key-status` を使用する (AK-05 と同じ規約)。
    // `is_expired` は ApiKeyResponse の computed field で、
    // expires_at < now() のとき True (api/lib/models/api_key.py)。
    await expect(row).toHaveAttribute("data-key-status", "expired", {
      timeout: 5_000,
    });
  });
});
