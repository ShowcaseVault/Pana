# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# --- Capacitor ---------------------------------------------------------------
#
# Plugins are found by reflection: the bridge reads @CapacitorPlugin at runtime
# and calls @PluginMethod by name, so nothing in the compiled code references
# them and R8 sees them as unreachable. Stripped, the app builds cleanly and
# then fails on the device the moment a plugin is called -- which is the worst
# shape a build error can take.
-keep @com.getcapacitor.annotation.CapacitorPlugin public class * {
  @com.getcapacitor.annotation.PermissionCallback <methods>;
  @com.getcapacitor.annotation.ActivityCallback <methods>;
  @com.getcapacitor.annotation.PluginMethod <methods>;
}

-keep public class * extends com.getcapacitor.Plugin { *; }
-keepclassmembers class * extends com.getcapacitor.Plugin {
  @com.getcapacitor.PluginMethod <methods>;
}

# The bridge's JavaScript interface is called from the web view by name.
-keepclassmembers class * {
  @android.webkit.JavascriptInterface <methods>;
}

# Cordova plugins, kept for the same reason: named in XML, not in code.
-keep class org.apache.cordova.** { *; }

# --- Google sign-in ----------------------------------------------------------
#
# The credential libraries are reached through reflection in the same way.
-keep class com.google.android.gms.** { *; }
-keep class androidx.credentials.** { *; }
-dontwarn com.google.android.gms.**

# --- Serialization -----------------------------------------------------------
#
# Anything converted to or from JSON is matched by field name, which R8 would
# otherwise rename.
-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod

# Stack traces from a shrunk build are unreadable without these: the line
# numbers stay, and the original file name is hidden rather than kept.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
