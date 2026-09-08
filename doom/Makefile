# Compila doomgeneric con l'uscita sul DMD al posto di quella su X11.
#
#   make DOOMGENERIC=/percorso/di/doomgeneric/doomgeneric
#
# Il risultato e' un solo binario, `doom-dmd`, che disegna 320x200 in memoria,
# ne ritaglia una fascia, la riduce a 256x64 e la scrive su stdout. Non apre
# finestre e non vuole X.
#
# L'audio (dalla 5.5)
# -------------------
# Fino alla 5.4 qui c'era scritto "non vuole SDL e non fa suono", ed era vero:
# nessun modulo sonoro veniva compilato. Poi le Impostazioni hanno guadagnato
# una levetta "Audio di Doom" che non poteva funzionare, perche' il binario
# non aveva niente con cui suonare. Questo Makefile e' il posto dove quel
# difetto viveva.
#
# doomgeneric il modulo ce l'ha — `i_sdlsound.c` e `i_sdlmusic.c`, quelli di
# chocolate-doom — e lo cerca sotto il nome `DG_sound_module` quando
# FEATURE_SOUND e' definito. Servono SDL2 e SDL2_mixer.
#
# Se non ci sono, **non si fallisce**: si compila muto come prima. Una
# libreria mancante non deve impedire di giocare, e la pagina Doom dice se il
# binario e' muto e perche'.
#
#   make SOUND=0    forza la compilazione muta
#   make SOUND=1    la pretende, e fallisce se le librerie non ci sono
#
# I sorgenti di doomgeneric non stanno in questo repository: sono GPL2 e li
# scarica setup_doom.sh al momento dell'installazione.

DOOMGENERIC ?= /opt/doomgeneric/doomgeneric
OUT ?= doom-dmd
OBJDIR ?= build

CC ?= gcc
# -DDOOMGENERIC_RESX/RESY=320x200: doomgeneric scala di un fattore intero
# (xres / SCREENWIDTH), quindi chiedendogli la risoluzione nativa di Doom il
# fattore e' 1 e non c'e' nessuna scalatura da buttare via subito dopo.
CFLAGS += -O2 -Wall -DNORMALUNIX -DLINUX -D_DEFAULT_SOURCE \
          -DDOOMGENERIC_RESX=320 -DDOOMGENERIC_RESY=200 \
          -I$(DOOMGENERIC)
LDFLAGS +=
LIBS += -lm

# Le librerie ci sono? Lo chiede pkg-config, che e' la domanda giusta: se
# rispondesse "si" e poi il link fallisse, l'errore arriverebbe dopo due
# minuti di compilazione invece che subito.
SOUND ?= $(shell pkg-config --exists sdl2 SDL2_mixer 2>/dev/null && echo 1 || echo 0)

ifeq ($(SOUND),1)
CFLAGS += -DFEATURE_SOUND $(shell pkg-config --cflags sdl2 SDL2_mixer)
LIBS += $(shell pkg-config --libs sdl2 SDL2_mixer)
SRC_SOUND = i_sdlsound.c i_sdlmusic.c mus2mid.c gusconf.c
else
SRC_SOUND =
endif

SRC_DOOM = dummy.c am_map.c doomdef.c doomstat.c dstrings.c d_event.c \
	d_items.c d_iwad.c d_loop.c d_main.c d_mode.c d_net.c f_finale.c \
	f_wipe.c g_game.c hu_lib.c hu_stuff.c info.c i_cdmus.c i_endoom.c \
	i_joystick.c i_scale.c i_sound.c i_system.c i_timer.c memio.c \
	m_argv.c m_bbox.c m_cheat.c m_config.c m_controls.c m_fixed.c \
	m_menu.c m_misc.c m_random.c p_ceilng.c p_doors.c p_enemy.c \
	p_floor.c p_inter.c p_lights.c p_map.c p_maputl.c p_mobj.c \
	p_plats.c p_pspr.c p_saveg.c p_setup.c p_sight.c p_spec.c \
	p_switch.c p_telept.c p_tick.c p_user.c r_bsp.c r_data.c r_draw.c \
	r_main.c r_plane.c r_segs.c r_sky.c r_things.c sha1.c sounds.c \
	statdump.c st_lib.c st_stuff.c s_sound.c tables.c v_video.c \
	wi_stuff.c w_checksum.c w_file.c w_main.c w_wad.c z_zone.c \
	w_file_stdc.c i_input.c i_video.c doomgeneric.c $(SRC_SOUND)

OBJS = $(addprefix $(OBJDIR)/, $(SRC_DOOM:.c=.o)) $(OBJDIR)/doomgeneric_dmd.o

all: $(OUT)
ifeq ($(SOUND),1)
	@echo "  audio: SI (SDL2 + SDL2_mixer)"
else
	@echo "  audio: NO — mancano SDL2 e SDL2_mixer. Doom sara' muto."
	@echo "         sudo apt install libsdl2-dev libsdl2-mixer-dev, poi ricompila."
endif

$(OUT): $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJS) -o $@ $(LIBS)

# Gli oggetti dipendono dalle **opzioni**, non solo dai sorgenti.
#
# Senza questo, aggiungere -DFEATURE_SOUND non ricompila niente: nessun .c e'
# cambiato, e make considera tutto aggiornato. Ma quella flag cambia il
# significato dei sorgenti gia' compilati — `dummy.c` definisce uno stub di
# `I_InitTimidityConfig` proprio quando FEATURE_SOUND **non** c'e' — e si
# finisce a collegare oggetti incoerenti fra loro:
#
#   multiple definition of `I_InitTimidityConfig'
#
# che arriva in fondo, dopo due minuti di compilazione, e sembra un difetto
# della libreria invece che una ricompilazione mancata.
#
# L'impronta contiene le opzioni in uso. Cambiarle riscrive il file, e da li'
# ogni oggetto risulta vecchio: si ricompila tutto, una volta sola.
IMPRONTA = $(OBJDIR)/.opzioni

$(IMPRONTA): CONTROLLA | $(OBJDIR)
	@printf '%s\n' '$(CFLAGS) $(LIBS)' | cmp -s - $@ 2>/dev/null \
	  || printf '%s\n' '$(CFLAGS) $(LIBS)' > $@

CONTROLLA: ;
.PHONY: CONTROLLA

$(OBJS): $(IMPRONTA)

$(OBJDIR)/doomgeneric_dmd.o: doomgeneric_dmd.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR)/%.o: $(DOOMGENERIC)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR):
	mkdir -p $(OBJDIR)

clean:
	rm -rf $(OBJDIR) $(OUT)

.PHONY: all clean
