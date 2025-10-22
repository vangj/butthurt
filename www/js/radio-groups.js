/**
 * Shared radio group definitions used by both the build tooling and runtime code.
 * Each entry maps a PDF field to the corresponding HTML form controls and translation keys.
 */
export const radioGroupsDefinition = [
  {
    fieldName: "injury_question1",
    htmlName: "part_iii_1",
    options: [
      { value: "left", labelKey: "21" },
      { value: "right", labelKey: "22" },
      { value: "both", labelKey: "23" }
    ]
  },
  {
    fieldName: "injury_question2",
    htmlName: "part_iii_2",
    options: [
      { value: "yes", labelKey: "25" },
      { value: "no", labelKey: "26" },
      { value: "maybe", labelKey: "27" }
    ]
  },
  {
    fieldName: "injury_question3",
    htmlName: "part_iii_3",
    options: [
      { value: "yes", labelKey: "25" },
      { value: "no", labelKey: "26" },
      { value: "multiple", labelKey: "29" }
    ]
  },
  {
    fieldName: "injury_question4",
    htmlName: "part_iii_4",
    options: [
      { value: "yes", labelKey: "25" },
      { value: "no", labelKey: "26" },
      { value: "maybe", labelKey: "27" }
    ]
  }
];

