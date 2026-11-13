/* Compare all pairs of lines with CompareStringA(LOCALE_USER_DEFAULT, NORM_IGNORECASE),
   the call behind Delphi 7's AnsiCompareText. Output: one line per i with signs for all j. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    static char lines[4000][256]; int n = 0;
    FILE *f = fopen(argv[1], "rb");
    while (n < 4000 && fgets(lines[n], 256, f)) {
        size_t l = strlen(lines[n]);
        while (l && (lines[n][l-1] == '\n' || lines[n][l-1] == '\r')) lines[n][--l] = 0;
        n++;
    }
    fclose(f);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int r = CompareStringA(LOCALE_USER_DEFAULT, NORM_IGNORECASE, lines[i], -1, lines[j], -1) - 2;
            putchar(r < 0 ? '<' : r > 0 ? '>' : '=');
        }
        putchar('\n');
    }
    printf("LCID %lu\n", (unsigned long)GetUserDefaultLCID());
    return 0;
}
