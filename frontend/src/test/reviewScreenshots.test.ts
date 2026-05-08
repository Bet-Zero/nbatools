import { beforeEach, describe, expect, it, vi } from "vitest";
import { toPng } from "html-to-image";
import { downloadReviewScreenshots } from "../lib/reviewScreenshots";

vi.mock("html-to-image", () => ({
  toPng: vi.fn(),
}));

describe("downloadReviewScreenshots", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:review-screenshots"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("uses image fallbacks so broken remote images do not abort capture", async () => {
    let downloadedFilename = "";
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function click(this: HTMLAnchorElement) {
        downloadedFilename = this.download;
      });
    const element = document.createElement("section");
    const progress = vi.fn();

    vi.mocked(toPng).mockResolvedValue("data:image/png;base64,AAAA");

    await downloadReviewScreenshots(
      [{ element, shapeName: "Leaderboard Table" }],
      progress,
      new Date("2026-05-08T12:00:00"),
    );

    expect(toPng).toHaveBeenCalledWith(
      element,
      expect.objectContaining({
        fontEmbedCSS: "",
        imagePlaceholder: expect.stringMatching(/^data:image\/gif;base64,/),
        onImageErrorHandler: expect.any(Function),
        pixelRatio: 2,
      }),
    );
    expect(progress).toHaveBeenCalledWith({ current: 1, total: 1 });
    expect(downloadedFilename).toBe("review-screenshots-2026-05-08.zip");

    clickSpy.mockRestore();
  });
});

