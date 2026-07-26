'use client';

import { type ReactNode, createContext, createElement, useContext } from 'react';
import type { DishaLanguage } from '@/lib/disha-language';

type ConstraintCopy = {
  label: string;
  emptyValue: string;
};

export type DishaCopy = {
  welcome: {
    counsellorView: string;
    eyebrow: string;
    heading: string;
    description: string;
    voiceAction: string;
    voiceOutcome: string;
    voiceMeta: string;
    trustLine: string;
    mixedLanguagePromise: string;
    proofLabel: string;
    streams: {
      stem: string;
      commerce: string;
      creative: string;
      civilServices: string;
      defence: string;
      vocational: string;
      jobsAfter10th: string;
    };
    micLabel: string;
    micStartingLabel: string;
    micAriaLabel: string;
    micStartingAriaLabel: string;
    loadingStatus: string;
    micInstruction: string;
    languagePickerLabel: string;
    languagePickerLegend: string;
    languageOptions: Record<DishaLanguage, string>;
  };
  panel: {
    startAudio: string;
    ariaLabel: string;
    heading: string;
    subheading: string;
    testResult: string;
    strengths: string;
    practicalFit: string;
    constraints: {
      distance_from_home: ConstraintCopy;
      hostel_needed: ConstraintCopy;
      fee_ceiling: ConstraintCopy;
      family_permission: ConstraintCopy;
      scholarship_dependence: ConstraintCopy;
    };
    careerPaths: string;
    sources: string;
    pagePrefix: string;
    attentionNote: string;
    flags: {
      distress: string;
      family_pressure: string;
      choice_paralysis: string;
      self_harm: string;
    };
    listLimit: string;
    refusalPrefix: string;
    refusalSuffix: string;
  };
  /** The shape the conversation drew of the student: strengths, and what they
   *  keep weighing. Read back to them, never as a verdict. */
  pattern: {
    heading: string;
    subheading: string;
    strengthsHeading: string;
    weighsHeading: string;
    testHeading: string;
    empty: string;
  };
  /** Everything they can go and read for themselves after the call. */
  explore: {
    heading: string;
    subheading: string;
    pathsHeading: string;
    scholarshipsHeading: string;
    readingHeading: string;
    sourcesHeading: string;
    levelLabel: string;
    durationLabel: string;
    eligibilityLabel: string;
    jobsLabel: string;
    leadsToLabel: string;
    amountLabel: string;
    incomeCeilingLabel: string;
    stateLabel: string;
    openLink: string;
    pagePrefix: string;
    lockedTitle: string;
    lockedBody: string;
    lockedSkip: string;
    empty: string;
  };
  summary: {
    badge: string;
    heading: string;
    strengths: string;
    testResult: string;
    shortlist: string;
    emptyShortlist: string;
    nextSteps: string;
    parentsTitle: string;
    parentsBody: string;
    endCall: string;
    newConversation: string;
    counsellorView: string;
    disconnectWithConstraints: string;
    disconnectWithoutConstraints: string;
    rememberImportantStep: string;
    verifyShortlistStep: string;
    bringInterestStep: string;
  };
};

export const DISHA_COPY: Record<DishaLanguage, DishaCopy> = {
  hi: {
    welcome: {
      counsellorView: 'काउंसलर view',
      eyebrow: '10वीं / 12वीं के बाद',
      heading: 'आगे का रास्ता, आपकी बात से।',
      description: 'बातचीत से अपने लिए सही रास्ते समझिए।',
      voiceAction: 'दबाइए और अपनी भाषा में बोलिए — mix भी चलेगा।',
      voiceOutcome: 'Disha फीस, दूरी और परिवार की बात समझती है।',
      voiceMeta: '~5 मिनट · कोई form नहीं',
      trustLine: 'कोई कमीशन नहीं',
      mixedLanguagePromise: 'जैसे बोलते हैं, वैसे बोलिए — mix चलेगा।',
      proofLabel: '244 रास्ते · 7 दिशाएँ',
      streams: {
        stem: 'STEM',
        commerce: 'Commerce',
        creative: 'Creative',
        civilServices: 'Civil Services',
        defence: 'Defence',
        vocational: 'Vocational',
        jobsAfter10th: '10वीं के बाद नौकरी',
      },
      micLabel: 'बात शुरू करें',
      micStartingLabel: 'जुड़ रहे हैं…',
      micAriaLabel: 'बात शुरू करें — माइक्रोफ़ोन चालू करें',
      micStartingAriaLabel: 'Disha से जुड़ रहे हैं',
      loadingStatus: 'Disha से कॉल जुड़ रही है। कृपया रुकें।',
      micInstruction: 'एक बार दबाएँ, फिर बोलें',
      languagePickerLabel: 'भाषा',
      languagePickerLegend: 'Disha की शुरुआती भाषा चुनें',
      languageOptions: {
        hi: 'हिंदी',
        en: 'English',
        mr: 'मराठी',
        ta: 'தமிழ்',
      },
    },
    panel: {
      startAudio: 'आवाज़ शुरू करें',
      ariaLabel: 'बातचीत से मिली जानकारी',
      heading: 'आपकी बातों से',
      subheading: 'बिना फ़ॉर्म, बातचीत के दौरान',
      testResult: 'टेस्ट का नतीजा',
      strengths: 'आपकी ताकत',
      practicalFit: 'Practical fit',
      constraints: {
        distance_from_home: {
          label: 'घर से दूरी',
          emptyValue: 'Distance from home',
        },
        hostel_needed: {
          label: 'हॉस्टल',
          emptyValue: 'Hostel needed',
        },
        fee_ceiling: {
          label: 'फीस सीमा',
          emptyValue: 'Fee ceiling',
        },
        family_permission: {
          label: 'परिवार की सहमति',
          emptyValue: 'Family permission',
        },
        scholarship_dependence: {
          label: 'स्कॉलरशिप',
          emptyValue: 'Scholarship dependence',
        },
      },
      careerPaths: 'Career paths',
      sources: 'Sources',
      pagePrefix: 'p.',
      attentionNote: 'ध्यान देने वाली बात',
      flags: {
        distress: 'थोड़ा ठहरकर सुनना ज़रूरी है',
        family_pressure: 'परिवार का दबाव सामने आया',
        choice_paralysis: 'फैसला कठिन लग रहा है',
        self_harm: 'अभी किसी भरोसेमंद व्यक्ति का साथ ज़रूरी है',
      },
      listLimit: 'सूची की सीमा',
      refusalPrefix: 'पूछा गया:',
      refusalSuffix: '— मेरी list में नहीं है',
    },
    pattern: {
      heading: 'आपकी अपनी बनावट',
      subheading: 'ये आपकी बातों से निकला है — कोई टेस्ट का नंबर नहीं।',
      strengthsHeading: 'जो आप में साफ़ दिखा',
      weighsHeading: 'फैसला लेते वक़्त आप ये तौलते हैं',
      testHeading: 'आपके टेस्ट का नतीजा',
      empty: 'अगली बातचीत थोड़ी लंबी हुई तो यहाँ आपका pattern बनेगा।',
    },
    explore: {
      heading: 'अब खुद पढ़िए',
      subheading: 'जो बातचीत में निकला, उसके असली स्रोत — परिवार को भी दिखा सकते हैं।',
      pathsHeading: 'आपके रास्ते, विस्तार से',
      scholarshipsHeading: 'पैसे की मदद',
      readingHeading: 'किताब से, जस का तस',
      sourcesHeading: 'ये जानकारी कहाँ से आई',
      levelLabel: 'कब',
      durationLabel: 'कितने साल',
      eligibilityLabel: 'योग्यता',
      jobsLabel: 'काम',
      leadsToLabel: 'इसके आगे',
      amountLabel: 'राशि',
      incomeCeilingLabel: 'आय सीमा',
      stateLabel: 'राज्य',
      openLink: 'पूरा पढ़ें',
      pagePrefix: 'पेज',
      lockedTitle: 'बाक़ी संदर्भ खुले हैं — नंबर देकर सहेज लीजिए',
      lockedBody:
        'नंबर देने पर पूरी सूची आपके फ़ोन पर भेज दी जाएगी और अगली बातचीत यहीं से शुरू होगी।',
      lockedSkip: 'अभी नहीं, सब यहीं दिखा दीजिए',
      empty: 'इस बातचीत में कोई संदर्भ नहीं जुड़ा।',
    },
    summary: {
      badge: 'बातचीत का सार',
      heading: 'अब आगे की दिशा साफ़ है',
      strengths: 'आपकी ताकत',
      testResult: 'आपके टेस्ट का नतीजा',
      shortlist: 'आपकी shortlist',
      emptyShortlist: 'इस बातचीत में कोई verified path shortlist नहीं हुआ।',
      nextSteps: 'अगले कदम',
      parentsTitle: 'माता-पिता के लिए',
      parentsBody: 'परिवार के साथ साझा करने वाला सरल भाषा का सार अगले milestone में यहाँ आएगा।',
      endCall: 'बातचीत समाप्त करें',
      newConversation: 'नई बातचीत',
      counsellorView: 'काउंसलर view देखें',
      disconnectWithConstraints:
        'आज की बातचीत में आपकी {count} ज़रूरी परिस्थिति समझ में आई। इन्हें साथ रखकर अगला कदम चुनें।',
      disconnectWithoutConstraints:
        'आज की बातचीत यहीं रुकी। जब तैयार हों, अपनी पसंद और परिस्थिति पर फिर आराम से बात कर सकते हैं।',
      rememberImportantStep: 'आज की बातों में जो सबसे ज़रूरी लगा, उसे लिख लें।',
      verifyShortlistStep: 'Shortlist में से एक रास्ते की फीस, दूरी और eligibility verify करें।',
      bringInterestStep: 'अगली बातचीत में अपनी पसंद का एक subject या काम लेकर आएँ।',
    },
  },
  en: {
    welcome: {
      counsellorView: 'Counsellor view',
      eyebrow: 'After Class 10 / 12',
      heading: 'Find your next path.',
      description: 'Talk it through and find a path that fits you.',
      voiceAction: 'Press and speak in your own language — mixing is fine.',
      voiceOutcome: 'Disha listens for fees, distance and family needs.',
      voiceMeta: '~5 minutes · no form',
      trustLine: 'No commission',
      mixedLanguagePromise: 'Speak naturally — mixing languages is fine.',
      proofLabel: '244 paths · 7 streams',
      streams: {
        stem: 'STEM',
        commerce: 'Commerce',
        creative: 'Creative',
        civilServices: 'Civil Services',
        defence: 'Defence',
        vocational: 'Vocational',
        jobsAfter10th: 'Jobs after Class 10',
      },
      micLabel: 'Start talking',
      micStartingLabel: 'Connecting…',
      micAriaLabel: 'Start talking — turn on the microphone',
      micStartingAriaLabel: 'Connecting to Disha',
      loadingStatus: 'Your call with Disha is connecting. Please wait.',
      micInstruction: 'Press once, then speak',
      languagePickerLabel: 'Language',
      languagePickerLegend: "Choose Disha's starting language",
      languageOptions: {
        hi: 'हिंदी',
        en: 'English',
        mr: 'मराठी',
        ta: 'தமிழ்',
      },
    },
    panel: {
      startAudio: 'Start audio',
      ariaLabel: 'What we understood from the conversation',
      heading: 'From what you shared',
      subheading: 'During the conversation, without a form',
      testResult: 'Test result',
      strengths: 'Your strengths',
      practicalFit: 'Practical fit',
      constraints: {
        distance_from_home: {
          label: 'Distance from home',
          emptyValue: 'Not discussed yet',
        },
        hostel_needed: {
          label: 'Hostel',
          emptyValue: 'Not discussed yet',
        },
        fee_ceiling: {
          label: 'Fees budget',
          emptyValue: 'Not discussed yet',
        },
        family_permission: {
          label: 'Family permission',
          emptyValue: 'Not discussed yet',
        },
        scholarship_dependence: {
          label: 'Scholarship',
          emptyValue: 'Not discussed yet',
        },
      },
      careerPaths: 'Career paths',
      sources: 'Sources',
      pagePrefix: 'p.',
      attentionNote: 'Something to pay attention to',
      flags: {
        distress: 'We need to pause and listen',
        family_pressure: 'Family pressure came up',
        choice_paralysis: 'Making a choice feels difficult',
        self_harm: 'Support from someone you trust is important right now',
      },
      listLimit: 'List boundary',
      refusalPrefix: 'Asked about:',
      refusalSuffix: '— not on my list',
    },
    pattern: {
      heading: 'The shape of you',
      subheading: 'Drawn from what you said — not from a test score.',
      strengthsHeading: 'What came through clearly',
      weighsHeading: 'What you weigh when you decide',
      testHeading: 'Your test result',
      empty: 'A longer conversation next time will fill this in.',
    },
    explore: {
      heading: 'Now read it yourself',
      subheading: 'The actual sources behind this conversation — show them to your family too.',
      pathsHeading: 'Your paths, in detail',
      scholarshipsHeading: 'Help with money',
      readingHeading: 'Straight from the handbook',
      sourcesHeading: 'Where this came from',
      levelLabel: 'When',
      durationLabel: 'Length',
      eligibilityLabel: 'Eligibility',
      jobsLabel: 'Work',
      leadsToLabel: 'Leads to',
      amountLabel: 'Amount',
      incomeCeilingLabel: 'Income ceiling',
      stateLabel: 'State',
      openLink: 'Read the full page',
      pagePrefix: 'page',
      lockedTitle: 'The rest is open — leave a number and keep it',
      lockedBody:
        'Give a number and the full list goes to your phone, and the next conversation picks up here.',
      lockedSkip: 'Not now — just show me everything',
      empty: 'No references came up in this conversation.',
    },
    summary: {
      badge: 'Conversation summary',
      heading: 'Your next direction is clearer now',
      strengths: 'Your strengths',
      testResult: 'Your test result',
      shortlist: 'Your shortlist',
      emptyShortlist: 'No verified path was shortlisted in this conversation.',
      nextSteps: 'Next steps',
      parentsTitle: 'For parents',
      parentsBody:
        'A plain-language summary to share with your family will appear here in the next milestone.',
      endCall: 'End conversation',
      newConversation: 'New conversation',
      counsellorView: 'View counsellor screen',
      disconnectWithConstraints:
        'We understood {count} important parts of your situation today. Keep them in mind when choosing your next step.',
      disconnectWithoutConstraints:
        'The conversation paused here today. When you are ready, you can come back and talk about your interests and situation.',
      rememberImportantStep: 'Write down what felt most important in today’s conversation.',
      verifyShortlistStep:
        'Verify the fees, distance and eligibility for one path from your shortlist.',
      bringInterestStep: 'Bring one subject or kind of work you enjoy to the next conversation.',
    },
  },
  mr: {
    welcome: {
      counsellorView: 'काउन्सेलर view',
      eyebrow: '१०वी / १२वीनंतर',
      heading: 'पुढचा मार्ग, तुमच्या बोलण्यातून.',
      description: 'गप्पांमधून तुमच्यासाठी योग्य मार्ग समजून घ्या.',
      voiceAction: 'दाबा आणि तुमच्या भाषेत बोला — mix चालेल.',
      voiceOutcome: 'Disha फी, अंतर आणि घरचं म्हणणं समजून घेते.',
      voiceMeta: '~५ मिनिटं · form नाही',
      trustLine: 'कोणतंही commission नाही',
      mixedLanguagePromise: 'तुम्ही जसं बोलता तसं बोला — mix चालेल.',
      proofLabel: '२४४ मार्ग · ७ दिशा',
      streams: {
        stem: 'STEM',
        commerce: 'Commerce',
        creative: 'Creative',
        civilServices: 'Civil Services',
        defence: 'Defence',
        vocational: 'व्यावसायिक शिक्षण',
        jobsAfter10th: '१०वीनंतर नोकरी',
      },
      micLabel: 'बोलायला सुरुवात करा',
      micStartingLabel: 'जोडत आहोत…',
      micAriaLabel: 'बोलायला सुरुवात करा — मायक्रोफोन सुरू करा',
      micStartingAriaLabel: 'Dishaशी जोडत आहोत',
      loadingStatus: 'Dishaशी कॉल जोडला जात आहे. कृपया थांबा.',
      micInstruction: 'एकदा दाबा, मग बोला',
      languagePickerLabel: 'भाषा',
      languagePickerLegend: 'Dishaची सुरुवातीची भाषा निवडा',
      languageOptions: {
        hi: 'हिंदी',
        en: 'English',
        mr: 'मराठी',
        ta: 'தமிழ்',
      },
    },
    panel: {
      startAudio: 'आवाज सुरू करा',
      ariaLabel: 'संभाषणातून समजलेली माहिती',
      heading: 'तुमच्या बोलण्यातून',
      subheading: 'फॉर्मशिवाय, संभाषणादरम्यान',
      testResult: 'टेस्टचा निकाल',
      strengths: 'तुमच्या जमेच्या बाजू',
      practicalFit: 'व्यवहारात काय जुळतं',
      constraints: {
        distance_from_home: {
          label: 'घरापासूनचं अंतर',
          emptyValue: 'अजून चर्चा झालेली नाही',
        },
        hostel_needed: {
          label: 'हॉस्टेल',
          emptyValue: 'अजून चर्चा झालेली नाही',
        },
        fee_ceiling: {
          label: 'फीची मर्यादा',
          emptyValue: 'अजून चर्चा झालेली नाही',
        },
        family_permission: {
          label: 'कुटुंबाची परवानगी',
          emptyValue: 'अजून चर्चा झालेली नाही',
        },
        scholarship_dependence: {
          label: 'शिष्यवृत्ती',
          emptyValue: 'अजून चर्चा झालेली नाही',
        },
      },
      careerPaths: 'करिअरचे मार्ग',
      sources: 'स्रोत',
      pagePrefix: 'पृ.',
      attentionNote: 'लक्ष द्यायची गोष्ट',
      flags: {
        distress: 'थोडं थांबून ऐकणं गरजेचं आहे',
        family_pressure: 'कुटुंबाचा दबाव जाणवला',
        choice_paralysis: 'निवड करणं कठीण वाटत आहे',
        self_harm: 'आत्ता विश्वासू व्यक्तीची साथ घेणं गरजेचं आहे',
      },
      listLimit: 'यादीची मर्यादा',
      refusalPrefix: 'याबद्दल विचारलं:',
      refusalSuffix: '— माझ्या listमध्ये नाही',
    },
    pattern: {
      heading: 'तुमची स्वतःची ठेवण',
      subheading: 'हे तुमच्याच बोलण्यातून आलं आहे — कुठल्या टेस्टच्या गुणांतून नाही.',
      strengthsHeading: 'तुमच्यात स्पष्ट दिसलं ते',
      weighsHeading: 'निर्णय घेताना तुम्ही हे तोलता',
      testHeading: 'तुमच्या टेस्टचा निकाल',
      empty: 'पुढच्या वेळी संभाषण थोडं लांब झालं की इथे तुमची ठेवण दिसेल.',
    },
    explore: {
      heading: 'आता स्वतः वाचा',
      subheading: 'या संभाषणामागचे खरे स्रोत — घरच्यांनाही दाखवू शकता.',
      pathsHeading: 'तुमचे मार्ग, सविस्तर',
      scholarshipsHeading: 'पैशाची मदत',
      readingHeading: 'पुस्तकातून, जसंच्या तसं',
      sourcesHeading: 'ही माहिती कुठून आली',
      levelLabel: 'केव्हा',
      durationLabel: 'किती वर्षं',
      eligibilityLabel: 'पात्रता',
      jobsLabel: 'काम',
      leadsToLabel: 'याच्या पुढे',
      amountLabel: 'रक्कम',
      incomeCeilingLabel: 'उत्पन्न मर्यादा',
      stateLabel: 'राज्य',
      openLink: 'पूर्ण वाचा',
      pagePrefix: 'पान',
      lockedTitle: 'बाकीचे संदर्भ खुले आहेत — नंबर देऊन जपून ठेवा',
      lockedBody: 'नंबर दिल्यावर पूर्ण यादी तुमच्या फोनवर जाईल आणि पुढचं संभाषण इथूनच सुरू होईल.',
      lockedSkip: 'आता नको, सगळं इथेच दाखवा',
      empty: 'या संभाषणात कोणताही संदर्भ आला नाही.',
    },
    summary: {
      badge: 'संभाषणाचा सारांश',
      heading: 'पुढची दिशा आता स्पष्ट आहे',
      strengths: 'तुमच्या जमेच्या बाजू',
      testResult: 'तुमच्या टेस्टचा निकाल',
      shortlist: 'तुमची shortlist',
      emptyShortlist: 'या संभाषणात कोणताही verified मार्ग shortlist झाला नाही.',
      nextSteps: 'पुढची पावलं',
      parentsTitle: 'आई-वडिलांसाठी',
      parentsBody:
        'कुटुंबासोबत शेअर करता येईल असा सोप्या भाषेतला सारांश पुढच्या milestoneमध्ये इथे दिसेल.',
      endCall: 'संभाषण संपवा',
      newConversation: 'नवं संभाषण',
      counsellorView: 'काउन्सेलर view पाहा',
      disconnectWithConstraints:
        'आजच्या संभाषणात तुमच्या परिस्थितीतल्या {count} महत्त्वाच्या गोष्टी समजल्या. पुढचं पाऊल निवडताना त्या लक्षात ठेवा.',
      disconnectWithoutConstraints:
        'आजचं संभाषण इथे थांबलं. तयार असाल तेव्हा तुमची आवड आणि परिस्थिती याबद्दल पुन्हा निवांत बोलू शकता.',
      rememberImportantStep: 'आजच्या संभाषणात सर्वांत महत्त्वाचं काय वाटलं, ते लिहून ठेवा.',
      verifyShortlistStep: 'Shortlistमधल्या एका मार्गाची फी, अंतर आणि eligibility तपासून घ्या.',
      bringInterestStep: 'पुढच्या संभाषणात आवडता subject किंवा कामाचा प्रकार घेऊन या.',
    },
  },
  ta: {
    welcome: {
      counsellorView: 'ஆலோசகர் view',
      eyebrow: '10 / 12ஆம் வகுப்புக்குப் பிறகு',
      heading: 'அடுத்த பாதை, உங்கள் பேச்சிலிருந்து.',
      description: 'உரையாடி உங்களுக்கு ஏற்ற பாதையைப் புரிந்துகொள்ளுங்கள்.',
      voiceAction: 'அழுத்தி, உங்கள் மொழியில் பேசுங்கள் — கலந்து பேசலாம்.',
      voiceOutcome: 'கட்டணம், தூரம், குடும்பச் சூழலை Disha புரிந்துகொள்ளும்.',
      voiceMeta: '~5 நிமிடங்கள் · form இல்லை',
      trustLine: 'கமிஷன் இல்லை',
      mixedLanguagePromise: 'இயல்பாகப் பேசுங்கள் — மொழிகளைக் கலக்கலாம்.',
      proofLabel: '244 பாதைகள் · 7 திசைகள்',
      streams: {
        stem: 'STEM',
        commerce: 'வணிகம்',
        creative: 'படைப்புத் துறை',
        civilServices: 'குடிமைப் பணிகள்',
        defence: 'பாதுகாப்புத் துறை',
        vocational: 'தொழிற்கல்வி',
        jobsAfter10th: '10ஆம் வகுப்புக்குப் பிறகு வேலை',
      },
      micLabel: 'பேசத் தொடங்குங்கள்',
      micStartingLabel: 'இணைக்கப்படுகிறது…',
      micAriaLabel: 'பேசத் தொடங்குங்கள் — மைக்கை இயக்குங்கள்',
      micStartingAriaLabel: 'Disha-வுடன் இணைக்கப்படுகிறது',
      loadingStatus: 'Disha அழைப்பு இணைக்கப்படுகிறது. தயவுசெய்து காத்திருக்கவும்.',
      micInstruction: 'ஒருமுறை அழுத்தி, பிறகு பேசுங்கள்',
      languagePickerLabel: 'மொழி',
      languagePickerLegend: 'Disha-வின் தொடக்க மொழியைத் தேர்ந்தெடுக்கவும்',
      languageOptions: {
        hi: 'हिंदी',
        en: 'English',
        mr: 'मराठी',
        ta: 'தமிழ்',
      },
    },
    panel: {
      startAudio: 'ஒலியைத் தொடங்குங்கள்',
      ariaLabel: 'உரையாடலில் புரிந்துகொண்ட தகவல்கள்',
      heading: 'நீங்கள் பகிர்ந்ததிலிருந்து',
      subheading: 'form இல்லாமல், உரையாடலின்போது',
      testResult: 'தேர்வு முடிவு',
      strengths: 'உங்கள் பலங்கள்',
      practicalFit: 'நடைமுறைப் பொருத்தம்',
      constraints: {
        distance_from_home: {
          label: 'வீட்டிலிருந்து தூரம்',
          emptyValue: 'இன்னும் பேசவில்லை',
        },
        hostel_needed: {
          label: 'விடுதி',
          emptyValue: 'இன்னும் பேசவில்லை',
        },
        fee_ceiling: {
          label: 'கட்டண வரம்பு',
          emptyValue: 'இன்னும் பேசவில்லை',
        },
        family_permission: {
          label: 'குடும்பத்தின் அனுமதி',
          emptyValue: 'இன்னும் பேசவில்லை',
        },
        scholarship_dependence: {
          label: 'உதவித்தொகை',
          emptyValue: 'இன்னும் பேசவில்லை',
        },
      },
      careerPaths: 'தொழில் பாதைகள்',
      sources: 'ஆதாரங்கள்',
      pagePrefix: 'ப.',
      attentionNote: 'கவனிக்க வேண்டிய ஒன்று',
      flags: {
        distress: 'சற்று நின்று கவனமாகக் கேட்பது அவசியம்',
        family_pressure: 'குடும்ப அழுத்தம் பேசப்பட்டது',
        choice_paralysis: 'முடிவெடுப்பது கடினமாக இருக்கிறது',
        self_harm: 'இப்போது நம்பகமான ஒருவரின் துணை அவசியம்',
      },
      listLimit: 'பட்டியலின் வரம்பு',
      refusalPrefix: 'கேட்கப்பட்டது:',
      refusalSuffix: '— என் list-இல் இல்லை',
    },
    pattern: {
      heading: 'உங்கள் சொந்த வடிவம்',
      subheading: 'இது நீங்கள் சொன்னதிலிருந்து வந்தது — எந்தத் தேர்வு மதிப்பெண்ணிலிருந்தும் அல்ல.',
      strengthsHeading: 'உங்களில் தெளிவாகத் தெரிந்தது',
      weighsHeading: 'முடிவெடுக்கும்போது நீங்கள் எடைபோடுவது',
      testHeading: 'உங்கள் தேர்வு முடிவு',
      empty: 'அடுத்த முறை உரையாடல் சற்று நீண்டால் உங்கள் வடிவம் இங்கே தெரியும்.',
    },
    explore: {
      heading: 'இப்போது நீங்களே படியுங்கள்',
      subheading: 'இந்த உரையாடலுக்குப் பின்னால் உள்ள உண்மையான ஆதாரங்கள் — வீட்டிலும் காட்டலாம்.',
      pathsHeading: 'உங்கள் பாதைகள், விரிவாக',
      scholarshipsHeading: 'பணத்திற்கான உதவி',
      readingHeading: 'கையேட்டிலிருந்து, அப்படியே',
      sourcesHeading: 'இந்தத் தகவல் எங்கிருந்து வந்தது',
      levelLabel: 'எப்போது',
      durationLabel: 'எத்தனை ஆண்டு',
      eligibilityLabel: 'தகுதி',
      jobsLabel: 'வேலை',
      leadsToLabel: 'இதற்கு அடுத்து',
      amountLabel: 'தொகை',
      incomeCeilingLabel: 'வருமான வரம்பு',
      stateLabel: 'மாநிலம்',
      openLink: 'முழுவதையும் படிக்க',
      pagePrefix: 'பக்கம்',
      lockedTitle: 'மீதி ஆதாரங்கள் திறந்தே உள்ளன — எண் கொடுத்துச் சேமியுங்கள்',
      lockedBody:
        'எண் கொடுத்தால் முழுப் பட்டியலும் உங்கள் தொலைபேசிக்கு வரும், அடுத்த உரையாடல் இங்கிருந்தே தொடங்கும்.',
      lockedSkip: 'இப்போது வேண்டாம் — எல்லாவற்றையும் இங்கேயே காட்டுங்கள்',
      empty: 'இந்த உரையாடலில் எந்த ஆதாரமும் வரவில்லை.',
    },
    summary: {
      badge: 'உரையாடல் சுருக்கம்',
      heading: 'அடுத்த பாதை இப்போது தெளிவாக உள்ளது',
      strengths: 'உங்கள் பலங்கள்',
      testResult: 'உங்கள் தேர்வு முடிவு',
      shortlist: 'உங்கள் shortlist',
      emptyShortlist: 'இந்த உரையாடலில் verified பாதை எதுவும் shortlist செய்யப்படவில்லை.',
      nextSteps: 'அடுத்த படிகள்',
      parentsTitle: 'பெற்றோருக்கு',
      parentsBody:
        'குடும்பத்துடன் பகிரக்கூடிய எளிய மொழிச் சுருக்கம் அடுத்த milestone-இல் இங்கே வரும்.',
      endCall: 'உரையாடலை முடிக்கவும்',
      newConversation: 'புதிய உரையாடல்',
      counsellorView: 'ஆலோசகர் view-ஐப் பார்க்கவும்',
      disconnectWithConstraints:
        'இன்றைய உரையாடலில் உங்கள் சூழ்நிலையின் {count} முக்கிய அம்சங்களைப் புரிந்துகொண்டோம். அடுத்த படியைத் தேர்ந்தெடுக்கும்போது அவற்றை நினைவில் கொள்ளுங்கள்.',
      disconnectWithoutConstraints:
        'இன்றைய உரையாடல் இங்கே நின்றது. நீங்கள் தயாரானதும், உங்கள் விருப்பங்களையும் சூழ்நிலையையும் பற்றி மீண்டும் நிதானமாகப் பேசலாம்.',
      rememberImportantStep:
        'இன்றைய உரையாடலில் மிக முக்கியமாகத் தோன்றியதை எழுதி வைத்துக்கொள்ளுங்கள்.',
      verifyShortlistStep:
        'உங்கள் shortlist-இல் உள்ள ஒரு பாதையின் கட்டணம், தூரம், eligibility ஆகியவற்றைச் சரிபாருங்கள்.',
      bringInterestStep:
        'அடுத்த உரையாடலுக்கு உங்களுக்குப் பிடித்த ஒரு subject அல்லது வேலை வகையை எடுத்துவருங்கள்.',
    },
  },
};

const DishaCopyContext = createContext<DishaCopy | null>(null);

interface DishaCopyProviderProps {
  language: DishaLanguage;
  children: ReactNode;
}

export function DishaCopyProvider({ language, children }: DishaCopyProviderProps) {
  return createElement(DishaCopyContext.Provider, { value: DISHA_COPY[language] }, children);
}

export function useDishaCopy(): DishaCopy {
  const copy = useContext(DishaCopyContext);

  if (!copy) {
    throw new Error('useDishaCopy must be used within a DishaCopyProvider');
  }

  return copy;
}
