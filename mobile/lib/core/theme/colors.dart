import 'package:flutter/material.dart';

/// App color palette
class AppColors {
  AppColors._();

  // Primary colors
  static const Color primary = Color(0xFF2563EB); // Blue 600
  static const Color primaryLight = Color(0xFF60A5FA); // Blue 400
  static const Color primaryDark = Color(0xFF1E40AF); // Blue 800

  // Secondary colors
  static const Color secondary = Color(0xFF8B5CF6); // Violet 500
  static const Color secondaryLight = Color(0xFFA78BFA); // Violet 400
  static const Color secondaryDark = Color(0xFF6D28D9); // Violet 700

  // Accent colors
  static const Color accent = Color(0xFF10B981); // Emerald 500
  static const Color accentLight = Color(0xFF34D399); // Emerald 400
  static const Color accentDark = Color(0xFF059669); // Emerald 600

  // Neutral colors
  static const Color neutral100 = Color(0xFFF5F5F5);
  static const Color neutral200 = Color(0xFFE5E5E5);
  static const Color neutral300 = Color(0xFFD4D4D4);
  static const Color neutral400 = Color(0xFFA3A3A3);
  static const Color neutral500 = Color(0xFF737373);
  static const Color neutral600 = Color(0xFF525252);
  static const Color neutral700 = Color(0xFF404040);
  static const Color neutral800 = Color(0xFF262626);
  static const Color neutral900 = Color(0xFF171717);

  // Background colors
  static const Color backgroundLight = Color(0xFFFAFAFA);
  static const Color backgroundDark = Color(0xFF0F0F0F);
  static const Color surfaceLight = Colors.white;
  static const Color surfaceDark = Color(0xFF1A1A1A);
  static const Color cardLight = Colors.white;
  static const Color cardDark = Color(0xFF262626);

  // Text colors
  static const Color textPrimaryLight = Color(0xFF171717);
  static const Color textPrimaryDark = Color(0xFFFAFAFA);
  static const Color textSecondaryLight = Color(0xFF525252);
  static const Color textSecondaryDark = Color(0xFFA3A3A3);
  static const Color textTertiaryLight = Color(0xFF737373);
  static const Color textTertiaryDark = Color(0xFF737373);

  // Status colors
  static const Color success = Color(0xFF10B981); // Emerald 500
  static const Color successLight = Color(0xFFD1FAE5); // Emerald 100
  static const Color successDark = Color(0xFF065F46); // Emerald 900

  static const Color warning = Color(0xFFF59E0B); // Amber 500
  static const Color warningLight = Color(0xFFFEF3C7); // Amber 100
  static const Color warningDark = Color(0xFF78350F); // Amber 900

  static const Color error = Color(0xFFEF4444); // Red 500
  static const Color errorLight = Color(0xFFFEE2E2); // Red 100
  static const Color errorDark = Color(0xFF7F1D1D); // Red 900

  static const Color info = Color(0xFF3B82F6); // Blue 500
  static const Color infoLight = Color(0xFFDBEAFE); // Blue 100
  static const Color infoDark = Color(0xFF1E3A8A); // Blue 900

  // Agent colors
  static const Color supervisorColor = Color(0xFF8B5CF6); // Violet
  static const Color researcherColor = Color(0xFF3B82F6); // Blue
  static const Color coderColor = Color(0xFF10B981); // Emerald
  static const Color reviewerColor = Color(0xFFF59E0B); // Amber
  static const Color designerColor = Color(0xFFEC4899); // Pink

  // Terminal colors
  static const Color terminalBackground = Color(0xFF0C0C0C);
  static const Color terminalText = Color(0xFFE5E5E5);
  static const Color terminalGreen = Color(0xFF10B981);
  static const Color terminalRed = Color(0xFFEF4444);
  static const Color terminalYellow = Color(0xFFF59E0B);
  static const Color terminalBlue = Color(0xFF3B82F6);
  static const Color terminalMagenta = Color(0xFFEC4899);
  static const Color terminalCyan = Color(0xFF06B6D4);

  // Voice UI colors
  static const Color voiceWaveform = Color(0xFF3B82F6);
  static const Color voiceWaveformActive = Color(0xFF10B981);
  static const Color voiceBackground = Color(0xFF1E3A8A);

  // Border colors
  static const Color borderLight = Color(0xFFE5E5E5);
  static const Color borderDark = Color(0xFF404040);

  // Shadow colors
  static const Color shadowLight = Color(0x1A000000);
  static const Color shadowDark = Color(0x4D000000);

  // Overlay colors
  static const Color overlayLight = Color(0x80000000);
  static const Color overlayDark = Color(0xCC000000);

  // Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primary, secondary],
  );

  static const LinearGradient darkGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [neutral900, neutral800],
  );

  static const LinearGradient voiceGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [voiceBackground, primaryDark],
  );
}