/* Reproduce TBm.BuildBitmap (UBitmaps.pas) under Wine and print the pixels.
 *
 * The original draws the name of an object on a white 50 x 50 bitmap when no
 * bitmap file exists. Under Wine this happens for the files whose names
 * contain an umlaut (see docs/decisions/0013). This program does what Delphi 7's
 * TBitmap/TCanvas do there:
 *
 *   PixelFormat := pf8bit; Width := 50; Height := 50;
 *   Canvas.Brush.Color := clWhite;  Canvas.Rectangle(0, 0, 50, 50);   (black pen)
 *   Canvas.TextOut(5, 5, Name);     (default TFont: 'MS Sans Serif', 8 pt)
 *
 * and prints one line per row, '#' for black and '.' for white.
 *
 * Build:  i686-w64-mingw32-gcc -O1 -o wine_build_bitmap.exe wine_build_bitmap.c -lgdi32
 * Run:    WINEPREFIX=~/.wine-psi wine wine_build_bitmap.exe Bergdurchh%E4mmern1 ...
 *         (%XX stands for a byte in code page 1252, as Wine's argv cannot carry it)
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    HDC screen = GetDC(0);
    int logpixels = GetDeviceCaps(screen, LOGPIXELSY);
    ReleaseDC(0, screen);

    for (int a = 1; a < argc; a++) {
        char name[256];
        size_t k = 0;
        for (const char *c = argv[a]; *c && k < sizeof name - 1; c++) {
            unsigned v;
            if (c[0] == '%' && c[1] && c[2] && sscanf(c + 1, "%2x", &v) == 1) {
                name[k++] = (char)v;
                c += 2;
            } else {
                name[k++] = *c;
            }
        }
        name[k] = 0;
        struct {
            BITMAPINFOHEADER h;
            RGBQUAD pal[256];
        } bi;
        memset(&bi, 0, sizeof bi);
        bi.h.biSize = sizeof(BITMAPINFOHEADER);
        bi.h.biWidth = 50;
        bi.h.biHeight = 50;
        bi.h.biPlanes = 1;
        bi.h.biBitCount = 8;
        bi.h.biCompression = BI_RGB;
        bi.h.biClrUsed = 256;
        /* index 0 black, 255 white, the rest grey ramp: only black and white are drawn */
        for (int i = 0; i < 256; i++) {
            bi.pal[i].rgbRed = bi.pal[i].rgbGreen = bi.pal[i].rgbBlue = (BYTE)i;
        }
        void *bits = NULL;
        HDC dc = CreateCompatibleDC(0);
        HBITMAP bmp = CreateDIBSection(dc, (BITMAPINFO *)&bi, DIB_RGB_COLORS, &bits, NULL, 0);
        HGDIOBJ oldbmp = SelectObject(dc, bmp);

        HPEN pen = CreatePen(PS_SOLID, 1, RGB(0, 0, 0));
        HBRUSH brush = CreateSolidBrush(RGB(255, 255, 255));
        LOGFONTA lf;
        memset(&lf, 0, sizeof lf);
        lf.lfHeight = -MulDiv(8, logpixels, 72);
        lf.lfWeight = FW_NORMAL;
        lf.lfCharSet = DEFAULT_CHARSET;
        lf.lfOutPrecision = OUT_DEFAULT_PRECIS;
        lf.lfClipPrecision = CLIP_DEFAULT_PRECIS;
        lf.lfQuality = DEFAULT_QUALITY;
        lf.lfPitchAndFamily = DEFAULT_PITCH;
        strcpy(lf.lfFaceName, "MS Sans Serif");
        HFONT font = CreateFontIndirectA(&lf);

        SelectObject(dc, pen);
        SelectObject(dc, brush);
        SelectObject(dc, font);
        Rectangle(dc, 0, 0, 50, 50);
        SetBkColor(dc, RGB(255, 255, 255));
        SetBkMode(dc, OPAQUE);
        SetTextColor(dc, RGB(0, 0, 0));
        ExtTextOutA(dc, 5, 5, 0, NULL, name, (UINT)strlen(name), NULL);
        GdiFlush();

        char face[64];
        GetTextFaceA(dc, sizeof face, face);
        printf("name %s\nlogpixels %d face %s\n", name, logpixels, face);
        const BYTE *p = (const BYTE *)bits;
        for (int y = 0; y < 50; y++) {
            const BYTE *row = p + (49 - y) * 52; /* bottom-up, rows padded to 4 bytes */
            for (int x = 0; x < 50; x++) {
                BYTE v = row[x];
                putchar(v == 0 ? '#' : (v == 255 ? '.' : '?'));
            }
            putchar('\n');
        }
        SelectObject(dc, oldbmp);
        DeleteObject(bmp);
        DeleteObject(pen);
        DeleteObject(brush);
        DeleteObject(font);
        DeleteDC(dc);
    }
    return 0;
}
