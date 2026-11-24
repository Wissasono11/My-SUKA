// Dihasilkan dari design-system/tokens.json v2.0.0. Jangan edit manual.
import 'package:flutter/material.dart';

class MySukaColors {
  static const primary = Color(0xFF155E38);
  static const primaryDark = Color(0xFF0F4A2C);
  static const primarySoft = Color(0xFFE4F1E8);
  static const secondary = Color(0xFFC59B27);
  static const secondaryTextOnLight = Color(0xFF7A5A00);
  static const secondaryTextOnDark = Color(0xFFEBCB6B);
  static const background = Color(0xFFF8FAFC);
  static const surface = Color(0xFFFFFFFF);
  static const text = Color(0xFF14261B);
  static const textMuted = Color(0xFF44574B);
  static const textOnPrimary = Color(0xFFFFFFFF);
  static const textOnPrimaryMuted = Color(0xFFDCEBE2);
  static const border = Color(0xFFDCE7E0);
  static const borderStrong = Color(0xFFC3D5C9);
  static const borderControl = Color(0xFF769080);
  static const focus = Color(0xFF1C5DA8);
  static const focusOnDark = Color(0xFFFFFFFF);
  static const statusNew = Color(0xFF5E6E63);
  static const warning = Color(0xFFA8540A);
  static const warningSoft = Color(0xFFFBF0E4);
  static const warningBorder = Color(0xFFECD3B6);
  static const info = Color(0xFF1C5DA8);
  static const success = Color(0xFF1B7A43);
  static const danger = Color(0xFFB3261E);
}

ThemeData mySukaTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: MySukaColors.primary).copyWith(
    primary: MySukaColors.primary,
    onPrimary: MySukaColors.textOnPrimary,
    secondary: MySukaColors.secondary,
    surface: MySukaColors.surface,
    onSurface: MySukaColors.text,
    error: MySukaColors.danger,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: MySukaColors.background,
    fontFamily: 'Plus Jakarta Sans',
  );
}
