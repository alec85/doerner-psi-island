/* Winkel (Menue.Pas) on the x87 FPU with Delphi's control word $1332 (64-bit precision).
   Prints dx dy and the 64-bit real result as hex, for all integer vectors in [-R, R]^2. */
#include <stdio.h>
#include <string.h>
static long double fpatan(long double y, long double x) {
    long double r;
    __asm__ ("fpatan" : "=t"(r) : "0"(x), "u"(y) : "st(1)");
    return r;
}
static long double fldpi(void) { long double r; __asm__ ("fldpi" : "=t"(r)); return r; }
int main(void) {
    unsigned short cw = 0x1332;
    __asm__ volatile ("fldcw %0" :: "m"(cw));
    const int R = 160;
    long double pi = fldpi();
    for (int o = -R; o <= R; o++)
        for (int a = -R; a <= R; a++) {
            volatile long double w, res;
            if (a != 0) {
                volatile long double q = (long double)o / (long double)a;
                w = fpatan(q, 1.0L);
                if (o > 0) res = (a > 0) ? pi - w : (w < 0 ? -w : w);
                else       res = (a > 0) ? pi + (w < 0 ? -w : w) : 2 * pi - w;
            } else {
                res = (o > 0) ? pi / 2 : 3 * pi / 2;
            }
            double d = (double)res;
            unsigned long long bits; memcpy(&bits, &d, 8);
            printf("%d %d %016llx\n", o, a, bits);
        }
    return 0;
}
