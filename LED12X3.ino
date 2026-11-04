
#include <LedControl.h>
#include "frames.h"

// Три незалежні групи по 4 матриці
LedControl matrix(12, 11, 10, 4);
LedControl matrix1(12, 11, 9, 4);
LedControl matrix2(12, 11, 8, 4);

// Фізичний порядок плат: зверху вниз
LedControl* boards[3] = {
  &matrix2,
  &matrix1,
  &matrix
};

// Лічильник кадрів
uint16_t currentFrame = 0;

// Час останнього оновлення
unsigned long previousFrameTime = 0;


// Ініціалізація однієї плати
void initializeGroup(LedControl &group) {

  for (int device = 0; device < 4; device++) {

    group.shutdown(device, false);
    group.setIntensity(device, 4);
    group.clearDisplay(device);

  }
}


// Виведення одного кадру на всі 12 матриць
void displayFrame(uint16_t frameIndex) {

  if (frameIndex >= FRAME_COUNT) {
    return;
  }

  for (int y = 0; y < FRAME_HEIGHT; y++) {

    int boardIndex = y / 8;
    int localRow = y % 8;

    for (int chunk = 0; chunk < 4; chunk++) {

      int device = 3 - chunk;

      byte pixelData = pgm_read_byte(
        &videoFrames[frameIndex][y * 4 + chunk]
      );

      boards[boardIndex]->setRow(
        device,
        localRow,
        pixelData
      );

    }
  }
}


void setup() {

  initializeGroup(matrix);
  initializeGroup(matrix1);
  initializeGroup(matrix2);

  // Показуємо перше серце
  displayFrame(0);

  previousFrameTime = millis();
}


void loop() {

  unsigned long currentTime = millis();

  if (currentTime - previousFrameTime >= FRAME_INTERVAL_MS) {

    previousFrameTime = currentTime;

    currentFrame++;

    // Повертаємося до першого кадру
    if (currentFrame >= FRAME_COUNT) {
      currentFrame = 0;
    }

    displayFrame(currentFrame);

  }
}
