#include "line_receiver.h"
int LineReceiver_Push(LineReceiver *r, unsigned char c)
{
    if (!r) return -1;
    if (c == '\n') {
        if (r->dropping) { r->dropping = 0; r->used = 0; return 0; }
        if (r->used && r->data[r->used - 1] == '\r') --r->used;
        r->data[r->used] = 0;
        int ready = r->used != 0;
        r->used = 0;
        return ready;
    }
    if (r->dropping) return 0;
    if ((c < 32 && c != '\r') || c > 126 || r->used >= sizeof(r->data) - 1) {
        r->dropping = 1; r->used = 0; return -1;
    }
    r->data[r->used++] = (char)c;
    return 0;
}
