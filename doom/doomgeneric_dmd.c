/*
 * doomgeneric_dmd — Doom su un pannello DMD da 256x64.
 *
 * Copyright (C) 2026 kWGillo
 *
 * Questo file si compila insieme a doomgeneric, che discende dai sorgenti di
 * Doom rilasciati da id Software sotto GNU GPL versione 2 o successiva: per
 * questo il file porta la stessa licenza del programma di cui entra a far
 * parte, e non la GPLv3 del resto del progetto. Il servizio DMD non ci si
 * collega: lo avvia come processo separato e gli parla da una pipe.
 *
 *   This program is free software; you can redistribute it and/or modify it
 *   under the terms of the GNU General Public License as published by the
 *   Free Software Foundation; either version 2 of the License, or (at your
 *   option) any later version.
 *
 * ---------------------------------------------------------------------------
 *
 * Il problema di far stare Doom su un DMD non e' la potenza di calcolo — e'
 * software del 1993 — ma la forma dello schermo. Doom disegna 320x200, cioe'
 * 1,6:1; il pannello e' 256x64, cioe' 4:1. Schiacciando il fotogramma intero
 * su 64 righe un nemico diventa alto otto pixel e non si distingue da un
 * barile.
 *
 * Quindi non si schiaccia: si ritaglia una **fascia** attorno all'orizzonte e
 * si butta via il resto. In Doom il pavimento e il soffitto sono esattamente
 * dove non succede niente, mentre i nemici stanno sulla linea dello sguardo.
 * La fascia si scala di 5:4 in larghezza (320 -> 256) e di quanto serve in
 * altezza, con una media a scatola: a questa dimensione l'antialiasing e' cio'
 * che rende leggibile una figura, non un lusso.
 *
 * La barra di stato non entra e non serve: vita e munizioni le ridisegna il
 * servizio DMD con il suo font, come fa per il radar. Qui si emette solo
 * l'immagine.
 *
 * Protocollo, tenuto volutamente stupido:
 *   - stdout: fotogrammi grezzi RGB888 da 256*64*3 = 49152 byte, uno dietro
 *     l'altro, senza intestazione. La dimensione e' fissa, quindi non serve.
 *   - stdin: eventi di tastiera, due byte ciascuno — [stato, codice], stato 1
 *     premuto e 0 rilasciato, codice nella numerazione di doomkeys.h.
 *   - stderr: i messaggi di Doom, che finiscono nel journal.
 *
 * Niente socket: una pipe non si lascia dietro file, non ha permessi da
 * sbagliare e muore insieme al processo.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <math.h>
#include <time.h>

#include "doomgeneric.h"
#include "doomkeys.h"

#define USCITA_L 256
#define USCITA_A 64
#define USCITA_BYTE (USCITA_L * USCITA_A * 3)

/* Fascia ritagliata dai 200 righe di Doom. I valori predefiniti sono il
 * risultato della prova sul pannello: 96 righe a partire dalla 36 tengono
 * dentro l'orizzonte, i nemici e la canna dell'arma, e lasciano fuori il
 * cielo e la barra di stato (che comincia a 168). */
static int fascia_alto = 36;
static int fascia_altezza = 96;

/* Doom e' un gioco buio, e un pannello LED non ha il nero di un CRT: senza
 * una correzione di gamma sul DMD si vede una macchia scura. */
static double gamma_valore = 0.70;
static unsigned char gamma_tabella[256];

static unsigned char uscita[USCITA_BYTE];

/* Doom scrive i suoi messaggi con printf, cioe' su stdout, che qui e' il
 * flusso dei fotogrammi: una riga di testo in mezzo a un'immagine sfasa tutto
 * quello che viene dopo. All'avvio si mette da parte il vero stdout su un
 * descrittore proprio e si fa puntare il numero 1 a stderr, cosi' i messaggi
 * di Doom finiscono nel journal insieme ai nostri. */
static int fd_frame = STDOUT_FILENO;

/* Il pannello disegna a 30 fps e Doom gira a 35 tic al secondo: lasciarlo
 * correre a settanta vuol dire buttare via meta' dei fotogrammi dopo averli
 * calcolati, e su un Pi quel lavoro sprecato si sente. */
#define PERIODO_MS 28   /* ~35 fps */
static uint32_t ultimo_frame_ms = 0;

/* ------------------------------------------------------------------ tempo */

uint32_t DG_GetTicksMs(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

void DG_SleepMs(uint32_t ms)
{
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

/* ------------------------------------------------------------------ tasti */

/* Lo stdin e' non bloccante: se non c'e' niente da leggere, Doom deve andare
 * avanti a girare invece di fermarsi ad aspettare un tasto che non arriva. */
int DG_GetKey(int* pressed, unsigned char* key)
{
    unsigned char coppia[2];
    ssize_t letti = read(STDIN_FILENO, coppia, 2);
    if (letti == 2) {
        *pressed = coppia[0] ? 1 : 0;
        *key = coppia[1];
        return 1;
    }
    /* Una lettura parziale non dovrebbe capitare con scritture da due byte,
     * ma se capita si completa: perdere meta' evento vorrebbe dire un tasto
     * che resta premuto per sempre. */
    if (letti == 1) {
        unsigned char resto;
        int tentativi = 0;
        while (read(STDIN_FILENO, &resto, 1) != 1 && tentativi++ < 1000) {
            DG_SleepMs(1);
        }
        *pressed = coppia[0] ? 1 : 0;
        *key = resto;
        return 1;
    }
    return 0;
}

/* ------------------------------------------------------------- fotogramma */

static void prepara_gamma(void)
{
    int i;
    for (i = 0; i < 256; i++) {
        double v = pow(i / 255.0, gamma_valore) * 255.0;
        gamma_tabella[i] = (unsigned char)(v > 255.0 ? 255.0 : v);
    }
}

/*
 * Ritaglia la fascia e la riduce a 256x64 con una media a scatola.
 *
 * Ogni pixel d'uscita raccoglie il rettangolo di sorgente che gli compete e
 * ne fa la media. A 256x64 la media conta piu' della velocita': una scala
 * "al pixel piu' vicino" fa sparire una figura sottile a seconda di dove
 * cade, mentre la media la lascia come ombra — e su un DMD un'ombra si vede.
 */
static void riduci(const pixel_t* sorgente)
{
    int ux, uy;
    for (uy = 0; uy < USCITA_A; uy++) {
        int y0 = fascia_alto + (uy * fascia_altezza) / USCITA_A;
        int y1 = fascia_alto + ((uy + 1) * fascia_altezza) / USCITA_A;
        if (y1 <= y0) y1 = y0 + 1;
        if (y1 > DOOMGENERIC_RESY) y1 = DOOMGENERIC_RESY;

        for (ux = 0; ux < USCITA_L; ux++) {
            int x0 = (ux * DOOMGENERIC_RESX) / USCITA_L;
            int x1 = ((ux + 1) * DOOMGENERIC_RESX) / USCITA_L;
            unsigned int r = 0, g = 0, b = 0, n = 0;
            int x, y;
            if (x1 <= x0) x1 = x0 + 1;
            if (x1 > DOOMGENERIC_RESX) x1 = DOOMGENERIC_RESX;

            for (y = y0; y < y1; y++) {
                const pixel_t* riga = sorgente + (size_t)y * DOOMGENERIC_RESX;
                for (x = x0; x < x1; x++) {
                    pixel_t p = riga[x];
                    r += (p >> 16) & 0xff;
                    g += (p >> 8) & 0xff;
                    b += p & 0xff;
                    n++;
                }
            }
            if (!n) n = 1;
            {
                unsigned char* out = uscita + ((size_t)uy * USCITA_L + ux) * 3;
                out[0] = gamma_tabella[r / n];
                out[1] = gamma_tabella[g / n];
                out[2] = gamma_tabella[b / n];
            }
        }
    }
}

void DG_DrawFrame(void)
{
    size_t scritti = 0;
    uint32_t adesso = DG_GetTicksMs();

    /* Ritmo: si aspetta il tempo che manca invece di correre. Doom tiene il
     * proprio tempo di gioco per conto suo, quindi rallentare qui non
     * rallenta la partita — toglie solo fotogrammi che nessuno vedrebbe. */
    if (ultimo_frame_ms && adesso - ultimo_frame_ms < PERIODO_MS) {
        DG_SleepMs(PERIODO_MS - (adesso - ultimo_frame_ms));
    }
    ultimo_frame_ms = DG_GetTicksMs();

    riduci(DG_ScreenBuffer);
    while (scritti < USCITA_BYTE) {
        ssize_t n = write(fd_frame, uscita + scritti, USCITA_BYTE - scritti);
        if (n > 0) {
            scritti += (size_t)n;
            continue;
        }
        if (n < 0 && (errno == EINTR || errno == EAGAIN)) {
            continue;
        }
        /* Il servizio DMD ha chiuso la pipe: la sessione e' finita, e restare
         * a girare per nessuno vorrebbe dire un processo orfano che consuma
         * un core del Pi. */
        exit(0);
    }
}

void DG_SetWindowTitle(const char* title)
{
    (void)title;
}

void DG_Init(void)
{
    int flags = fcntl(STDIN_FILENO, F_GETFL, 0);
    if (flags != -1) {
        fcntl(STDIN_FILENO, F_SETFL, flags | O_NONBLOCK);
    }
    prepara_gamma();
}

/* -------------------------------------------------------------------- main */

int main(int argc, char** argv)
{
    /* Le opzioni della fascia si leggono qui e non si compilano dentro: la
     * taratura giusta si trova guardando il pannello, e ricompilare Doom a
     * ogni tentativo non e' un modo di lavorare. Quelle che Doom non
     * conosce vengono tolte prima di passargli la riga di comando. */
    int i, n = 0;
    char** passa;

    /* Prima di ogni altra cosa: mettere al sicuro il flusso dei fotogrammi.
     * Da qui in poi qualunque printf di Doom va nel log, non nell'immagine. */
    fd_frame = dup(STDOUT_FILENO);
    if (fd_frame < 0) {
        fprintf(stderr, "[doom-dmd] non riesco a duplicare stdout\n");
        return 1;
    }
    if (dup2(STDERR_FILENO, STDOUT_FILENO) < 0) {
        fprintf(stderr, "[doom-dmd] non riesco a dirottare stdout\n");
        return 1;
    }
    setvbuf(stdout, NULL, _IOLBF, 0);

    passa = malloc(sizeof(char*) * (argc + 1));
    for (i = 0; i < argc; i++) {
        if (!strncmp(argv[i], "--fascia-alto=", 14)) {
            fascia_alto = atoi(argv[i] + 14);
        } else if (!strncmp(argv[i], "--fascia-altezza=", 17)) {
            fascia_altezza = atoi(argv[i] + 17);
        } else if (!strncmp(argv[i], "--gamma=", 8)) {
            gamma_valore = atof(argv[i] + 8);
        } else {
            passa[n++] = argv[i];
        }
    }
    passa[n] = NULL;

    if (fascia_alto < 0) fascia_alto = 0;
    if (fascia_altezza < 8) fascia_altezza = 8;
    if (fascia_alto + fascia_altezza > DOOMGENERIC_RESY) {
        fascia_altezza = DOOMGENERIC_RESY - fascia_alto;
    }
    if (gamma_valore < 0.2) gamma_valore = 0.2;
    if (gamma_valore > 2.0) gamma_valore = 2.0;

    fprintf(stderr, "[doom-dmd] fascia %d..%d di %d, gamma %.2f\n",
            fascia_alto, fascia_alto + fascia_altezza, DOOMGENERIC_RESY,
            gamma_valore);

    doomgeneric_Create(n, passa);

    for (;;) {
        doomgeneric_Tick();
    }
    return 0;
}
