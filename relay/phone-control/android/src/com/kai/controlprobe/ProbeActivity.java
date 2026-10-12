package com.kai.controlprobe;

import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Visible, permission-free instrument for testing UI input on the owner's phone. */
public final class ProbeActivity extends Activity {
    private int taps;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (state != null) taps = state.getInt("taps", 0);
        ScrollView scroll = new ScrollView(this);
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(36, 100, 36, 100);
        TextView title = new TextView(this);
        title.setText("KAI Control Lab\nPrueba local de pantalla y controles");
        title.setTextSize(24);
        column.addView(title);
        TextView note = new TextView(this);
        note.setText("Sin permisos, sin red y sin acceso a otras aplicaciones. El contador permite comprobar el efecto real de una pulsación.");
        column.addView(note);
        TextView count = new TextView(this);
        count.setTextSize(22);
        count.setText("PULSACIONES=" + taps);
        column.addView(count);
        Button button = new Button(this);
        button.setText("PROBAR PULSACIÓN");
        button.setContentDescription("KAI_TAP_TARGET");
        button.setOnClickListener(v -> count.setText("PULSACIONES=" + (++taps)));
        column.addView(button);
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("Texto de prueba");
        input.setContentDescription("KAI_TEXT_TARGET");
        column.addView(input);
        Button apply = new Button(this);
        apply.setText("COMPROBAR TEXTO");
        apply.setContentDescription("KAI_APPLY_TARGET");
        TextView echo = new TextView(this);
        echo.setText("TEXTO=pendiente");
        apply.setOnClickListener(v -> echo.setText("TEXTO=" + input.getText().toString()));
        column.addView(apply);
        column.addView(echo);
        for (int i = 1; i <= 14; i++) {
            TextView row = new TextView(this);
            row.setText("Zona de desplazamiento " + i);
            row.setPadding(0, 24, 0, 24);
            column.addView(row);
        }
        TextView end = new TextView(this);
        end.setText("FINAL_DESPLAZAMIENTO_KAI");
        column.addView(end);
        scroll.addView(column);
        setContentView(scroll);
    }
    @Override public void onSaveInstanceState(Bundle state) {
        state.putInt("taps", taps);
        super.onSaveInstanceState(state);
    }
}
