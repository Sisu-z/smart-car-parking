#ifndef LINE_RECEIVER_H
#define LINE_RECEIVER_H
#include <stddef.h>
/* 只在前台消费字节；ISR 应使用平台有界队列。长行整行丢弃。 */
typedef struct { char data[96]; size_t used; int dropping; } LineReceiver;
/* 1=完整行，0=未完成，-1=坏字节/超长；返回 1 后立即消费 data。 */
int LineReceiver_Push(LineReceiver *, unsigned char byte);
#endif
