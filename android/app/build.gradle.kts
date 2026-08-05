plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "dev.yury.mathmark"
    compileSdk = 37

    defaultConfig {
        applicationId = "dev.yury.mathmark"
        minSdk = 30
        targetSdk = 37
        versionCode = 8
        versionName = "1.4.1"
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = false
            // один и тот же ключ у всех сборок: иначе обновление не встанет поверх
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    // страница чтения и KaTeX лежат в общей папке — та же самая, что у десктопа.
    // Иначе телефон и компьютер со временем начнут рисовать по-разному.
    sourceSets["main"].assets.srcDirs(
        "src/main/assets",
        "../../shared/reader",
        "../../shared/prompt",
        "../../shared/i18n",
        "../../shared/whatsnew",
        "../../shared/meta",
    )

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.06.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.core:core-ktx:1.19.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.11.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.0")

    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")
}
