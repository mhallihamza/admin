import type { Locale } from "./config";

export interface Dictionary {
  meta: { title: string; description: string };
  brand: string;
  header: {
    nav: { howItWorks: string; services: string; sources: string; faq: string };
    login: string;
    createAccount: string;
    menuOpen: string;
    menuClose: string;
  };
  hero: {
    headline: string;
    subtitle: string;
    searchPlaceholder: string;
    search: string;
    examplesLabel: string;
    exampleChips: string[];
    chat: {
      title: string;
      placeholder: string;
      button: string;
      examplesLabel: string;
      chips: string[];
      disclaimer: string;
      unavailable: string;
    };
  };
  howItWorks: {
    title: string;
    items: { title: string; description: string }[];
  };
  services: {
    title: string;
    items: { title: string; description: string }[];
  };
  sources: {
    title: string;
    points: { title: string; description: string }[];
  };
  faq: {
    title: string;
    items: { question: string; answer: string }[];
  };
  footer: {
    platformTitle: string;
    platformLinks: { label: string; href: string }[];
    legalTitle: string;
    legalLinks: { label: string; href: string }[];
    contactTitle: string;
    contactLinks: { label: string; href: string }[];
    languageTitle: string;
    languageLinks: { label: string; href: string; locale: Locale }[];
    copyright: string;
  };
  auth: {
    login: {
      title: string;
      emailLabel: string;
      passwordLabel: string;
      submit: string;
      submitting: string;
      errorInvalid: string;
      errorNotConfirmed: string;
      errorGeneric: string;
      errorConfig: string;
      noAccount: string;
      createAccountLink: string;
    };
    register: {
      title: string;
      emailLabel: string;
      passwordLabel: string;
      confirmPasswordLabel: string;
      submit: string;
      submitting: string;
      errorMismatch: string;
      errorShort: string;
      errorAlreadyExists: string;
      errorGeneric: string;
      errorConfig: string;
      haveAccount: string;
      loginLink: string;
      successMessage: string;
    };
  };
  dashboard: {
    sidebar: {
      groups: {
        main: string;
        citizen: string;
        review: string;
        content: string;
        administration: string;
        security: string;
      };
      items: {
        dashboard: string;
        chat: string;
        conversations: string;
        saved: string;
        processes: string;
        reviewQueue: string;
        documents: string;
        overview: string;
        usersRoles: string;
        permissions: string;
        workflows: string;
        security: string;
      };
      disabledHint: string;
    };
    topbar: {
      notifications: string;
      notificationsEmpty: string;
      userMenu: string;
      signOut: string;
      menuOpen: string;
      menuClose: string;
    };
    home: {
      welcome: string;
      rolesLabel: string;
      phaseNote: string;
    };
    accessDenied: {
      title: string;
      message: string;
      backHome: string;
    };
    roles: {
      VISITOR: string;
      CITIZEN: string;
      EMPLOYEE: string;
      CONTENT_APPROVER: string;
      SYSTEM_ADMIN: string;
      SECURITY_AUDITOR: string;
      PLATFORM_SUPER_ADMIN: string;
    };
    citizen: {
      chatTitle: string;
      chatPlaceholder: string;
      send: string;
      engineNote: string;
      stepsLabel: string;
      documentsLabel: string;
      administrationLabel: string;
      sourcesLabel: string;
      saveProcedure: string;
      saved: string;
      requestReview: string;
      reviewRequested: string;
      suggestedProcedures: string;
      savedProcedures: string;
      historyTitle: string;
      historyEmpty: string;
      savedTitle: string;
      savedEmpty: string;
      messagesLabel: string;
      updatedLabel: string;
    };
    employee: {
      queueTitle: string;
      colId: string;
      colQuestion: string;
      colRisk: string;
      colStatus: string;
      colCreated: string;
      colService: string;
      detailTitle: string;
      questionLabel: string;
      proposedAnswerLabel: string;
      evidenceLabel: string;
      actionsLabel: string;
      approve: string;
      correct: string;
      reject: string;
      transfer: string;
      transferTo: string;
      transferConfirm: string;
      noteLabel: string;
      noteRequired: string;
      backToList: string;
      actionDone: string;
      risks: Record<string, string>;
      statuses: Record<string, string>;
    };
    admin: {
      overviewTitle: string;
      kpiUsers: string;
      kpiRequests: string;
      kpiBlocked: string;
      kpiErrors: string;
      chartRequests: string;
      chartBlocked: string;
      usersTitle: string;
      colEmail: string;
      colName: string;
      colRoles: string;
      colState: string;
      colActions: string;
      active: string;
      userDisabled: string;
      userDisable: string;
      userEnable: string;
      changeRole: string;
      save: string;
      cancel: string;
      auditNote: string;
      auditRecent: string;
      documentsTitle: string;
      dropzone: string;
      allowedTypes: string;
      sizeLimit: string;
      invalidType: string;
      tooLarge: string;
      uploadNote: string;
      colTitle: string;
      colFile: string;
      colSize: string;
      colStatus: string;
      colDocActions: string;
      docStatuses: Record<string, string>;
      sendIndexing: string;
      sendReview: string;
      approve: string;
      reject: string;
      disable: string;
      retry: string;
      previewTitle: string;
      previewEmpty: string;
      permissionsTitle: string;
      colAgent: string;
      colTool: string;
      colOperation: string;
      colAllowed: string;
      allow: string;
      deny: string;
      permissionsNote: string;
      workflowsTitle: string;
      colWorkflow: string;
      colStarted: string;
      colDuration: string;
      colWfStatus: string;
      wfStatuses: Record<string, string>;
    };
    security: {
      title: string;
      incidentsTitle: string;
      colTime: string;
      colAttack: string;
      colRisk: string;
      colDecision: string;
      colReason: string;
      colContent: string;
      contentHidden: string;
      reveal: string;
      reasonLabel: string;
      reasonPlaceholder: string;
      confirmReveal: string;
      cancel: string;
      revealNote: string;
      blockedTitle: string;
      colRoute: string;
      redTeamTitle: string;
      colScenario: string;
      colResult: string;
      resultBlocked: string;
      resultPartial: string;
      resultFailed: string;
      redTeamDetailsHidden: string;
      details: string;
      auditTitle: string;
      colActor: string;
      colAction: string;
      colEntity: string;
      attacks: Record<string, string>;
    };
  };
  common: { backHome: string };
}

const fr: Dictionary = {
  meta: {
    title: "Guide Administratif",
    description:
      "Assistant aux démarches administratives au Maroc : procédures officielles, documents requis et sources légales, en français et en arabe.",
  },
  brand: "Guide Administratif",
  header: {
    nav: {
      howItWorks: "Comment ça marche",
      services: "Services",
      sources: "Sources",
      faq: "FAQ",
    },
    login: "Se connecter",
    createAccount: "Créer un compte",
    menuOpen: "Ouvrir le menu",
    menuClose: "Fermer le menu",
  },
  hero: {
    headline: "Vos démarches administratives, expliquées simplement",
    subtitle:
      "Posez votre question et obtenez la procédure officielle, les documents requis et les sources légales — en français ou en arabe.",
    searchPlaceholder: "Ex. : comment renouveler ma carte nationale d'identité ?",
    search: "Rechercher",
    examplesLabel: "Essayez :",
    exampleChips: [
      "Renouveler un passeport",
      "Inscrire un nouveau-né à l'état civil",
      "Obtenir une attestation de résidence",
    ],
        chat: {
      title: "Posez votre question — sans compte",
      placeholder: "Ex. : comment obtenir le certificat d'héritage ?",
      button: "Demander",
      examplesLabel: "Essayez :",
      chips: [
        "Comment obtenir le certificat d'héritage ?",
        "Qui doit déclarer un décès et dans quel délai ?",
        "Comment immatriculer une société au registre du commerce ?",
      ],
      disclaimer:
        "Réponses générées uniquement à partir des documents officiels approuvés de la plateforme, avec leurs références (document, article, version). Aucune donnée personnelle n'est requise.",
      unavailable:
        "Le service de réponse est momentanément indisponible. Réessayez dans un instant.",
    },
  },
  howItWorks: {
    title: "Comment ça marche",
    items: [
      {
        title: "Posez votre question",
        description:
          "Décrivez votre situation en français ou en arabe, avec vos propres mots.",
      },
      {
        title: "Recevez la procédure",
        description:
          "Obtenez les étapes, les documents requis et l'administration compétente.",
      },
      {
        title: "Vérifiez les sources",
        description:
          "Chaque réponse cite les documents officiels approuvés et leur version en vigueur.",
      },
    ],
  },
  services: {
    title: "Services",
    items: [
      {
        title: "Procédures",
        description:
          "Les étapes officielles de vos démarches, expliquées pas à pas.",
      },
      {
        title: "Documents requis",
        description: "La liste des pièces à fournir pour chaque dossier.",
      },
      {
        title: "Administration compétente",
        description: "Le bon guichet et l'organisme à contacter.",
      },
      {
        title: "Références légales",
        description:
          "Les textes et articles cités, avec leur version en vigueur.",
      },
      {
        title: "Procédures enregistrées",
        description:
          "Conservez vos démarches pour les retrouver plus tard.",
      },
      {
        title: "Demande de revue humaine",
        description:
          "Un agent vérifie les cas sensibles avant toute réponse définitive.",
      },
    ],
  },
  sources: {
    title: "Sources officielles et confiance",
    points: [
      {
        title: "Documents approuvés uniquement",
        description:
          "Les réponses s'appuient exclusivement sur des documents officiels validés par la plateforme.",
      },
      {
        title: "Textes versionnés",
        description:
          "Chaque loi est datée et versionnée ; seule la version en vigueur est utilisée.",
      },
      {
        title: "Revue humaine",
        description:
          "Les cas sensibles sont transmis à un agent avant toute réponse définitive.",
      },
    ],
  },
  faq: {
    title: "Questions fréquentes",
    items: [
      {
        question: "D'où viennent les réponses de l'assistant ?",
        answer:
          "Les réponses sont générées uniquement à partir de documents officiels approuvés et versionnés par la plateforme. Aucune réponse n'est inventée.",
      },
      {
        question: "Les informations fournies sont-elles juridiquement opposables ?",
        answer:
          "Les réponses ont une valeur indicative. Pour un acte officiel, référez-vous toujours au texte en vigueur ou à l'administration compétente.",
      },
      {
        question: "Puis-je utiliser la plateforme en arabe ?",
        answer:
          "Oui. L'interface et les réponses sont disponibles en français et en arabe, avec un affichage adapté à la lecture de droite à gauche.",
      },
      {
        question: "Que se passe-t-il si ma question est sensible ?",
        answer:
          "Les cas sensibles sont transmis à un agent pour revue humaine avant qu'une réponse définitive ne vous soit fournie.",
      },
      {
        question: "Comment mes données sont-elles protégées ?",
        answer:
          "Vos conversations sont stockées de manière sécurisée et l'accès est strictement limité aux rôles autorisés, avec journalisation des accès.",
      },
      {
        question: "La création d'un compte est-elle obligatoire ?",
        answer:
          "Vous pouvez consulter les pages publiques sans compte. La connexion est requise pour poser des questions et enregistrer des procédures.",
      },
    ],
  },
  footer: {
    platformTitle: "Plateforme",
    platformLinks: [
      { label: "Comment ça marche", href: "#how-it-works" },
      { label: "Services", href: "#services" },
      { label: "Sources officielles", href: "#sources" },
    ],
    legalTitle: "Légal",
    legalLinks: [
      { label: "Confidentialité", href: "#" },
      { label: "Conditions d'utilisation", href: "#" },
    ],
    contactTitle: "Contact",
    contactLinks: [
      { label: "Centre d'aide", href: "#" },
      { label: "Signaler un problème", href: "#" },
    ],
    languageTitle: "Langue",
    languageLinks: [
      { label: "Français", href: "/fr", locale: "fr" },
      { label: "العربية", href: "/ar", locale: "ar" },
    ],
    copyright: "© 2026 Guide Administratif — projet de démonstration.",
  },
  auth: {
    login: {
      title: "Se connecter",
      emailLabel: "Adresse e-mail",
      passwordLabel: "Mot de passe",
      submit: "Se connecter",
      submitting: "Connexion…",
      errorInvalid: "E-mail ou mot de passe incorrect.",
      errorNotConfirmed:
        "Veuillez confirmer votre adresse e-mail avant de vous connecter.",
      errorGeneric: "Une erreur est survenue. Veuillez réessayer.",
      errorConfig:
        "La connexion n'est pas configurée : définissez NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY dans frontend/.env.local.",
      noAccount: "Pas encore de compte ?",
      createAccountLink: "Créer un compte",
    },
    register: {
      title: "Créer un compte",
      emailLabel: "Adresse e-mail",
      passwordLabel: "Mot de passe",
      confirmPasswordLabel: "Confirmer le mot de passe",
      submit: "Créer un compte",
      submitting: "Création…",
      errorMismatch: "Les mots de passe ne correspondent pas.",
      errorShort: "Le mot de passe doit contenir au moins 8 caractères.",
      errorAlreadyExists: "Un compte existe déjà avec cet e-mail.",
      errorGeneric: "Une erreur est survenue. Veuillez réessayer.",
      errorConfig:
        "La connexion n'est pas configurée : définissez NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY dans frontend/.env.local.",
      haveAccount: "Vous avez déjà un compte ?",
      loginLink: "Se connecter",
      successMessage:
        "Compte créé. Vérifiez votre boîte e-mail pour confirmer votre adresse si la confirmation est activée.",
    },
  },
  common: { backHome: "Retour à l'accueil" },
  dashboard: {
    sidebar: {
      groups: {
        main: "Principal",
        citizen: "Espace citoyen",
        review: "Revue humaine",
        content: "Contenus",
        administration: "Administration",
        security: "Sécurité",
      },
      items: {
        dashboard: "Tableau de bord",
        chat: "Assistant",
        conversations: "Historique des conversations",
        saved: "Procédures enregistrées",
        processes: "Mes démarches",
        reviewQueue: "File de revue",
        documents: "Gestion des documents",
        overview: "Vue d'ensemble",
        usersRoles: "Utilisateurs et rôles",
        permissions: "Permissions",
        workflows: "Monitor workflows",
        security: "Sécurité et audit",
      },
      disabledHint: "Disponible à partir de la phase suivante",
    },
    topbar: {
      notifications: "Notifications",
      notificationsEmpty: "Aucune notification.",
      userMenu: "Menu utilisateur",
      signOut: "Se déconnecter",
      menuOpen: "Ouvrir la navigation",
      menuClose: "Fermer la navigation",
    },
    home: {
      welcome: "Bienvenue",
      rolesLabel: "Vos rôles",
      phaseNote:
        "Vos sections utilisent maintenant les données réelles de la plateforme (compte, conversations, procédures enregistrées et démarches).",
    },
    accessDenied: {
      title: "Accès restreint",
      message:
        "Votre compte n'a pas le rôle nécessaire pour accéder à cet espace. Contactez l'administrateur si vous pensez qu'il s'agit d'une erreur.",
      backHome: "Retour à l'accueil",
    },
    roles: {
      VISITOR: "Visiteur",
      CITIZEN: "Citoyen",
      EMPLOYEE: "Agent",
      CONTENT_APPROVER: "Validateur de contenu",
      SYSTEM_ADMIN: "Administrateur système",
      SECURITY_AUDITOR: "Auditeur sécurité",
      PLATFORM_SUPER_ADMIN: "Super administrateur",
    },
    citizen: {
      chatTitle: "Assistant",
      chatPlaceholder: "Posez votre question…",
      send: "Envoyer",
      engineNote:
        "Les réponses proviennent du moteur officiel (source approuvées uniquement). Les conversations et procédures enregistrées sont sauvegardées dans votre compte.",
      stepsLabel: "Étapes",
      documentsLabel: "Documents requis",
      administrationLabel: "Administration compétente",
      sourcesLabel: "Sources",
      saveProcedure: "Enregistrer la procédure",
      saved: "Enregistrée",
      requestReview: "Demander une revue humaine",
      reviewRequested: "Transmis à la revue humaine",
      suggestedProcedures: "Procédures suggérées",
      savedProcedures: "Procédures enregistrées",
      historyTitle: "Historique des conversations",
      historyEmpty: "Aucune conversation pour le moment.",
      savedTitle: "Procédures enregistrées",
      savedEmpty: "Aucune procédure enregistrée pour le moment.",
      messagesLabel: "messages",
      updatedLabel: "Mise à jour",
    },
    employee: {
      queueTitle: "Cas à examiner",
      colId: "N° de cas",
      colQuestion: "Question",
      colRisk: "Niveau de risque",
      colStatus: "Statut",
      colCreated: "Créé le",
      colService: "Service",
      detailTitle: "Détail du cas",
      questionLabel: "Question",
      proposedAnswerLabel: "Réponse proposée",
      evidenceLabel: "Preuves légales utilisées",
      actionsLabel: "Actions",
      approve: "Approuver",
      correct: "Corriger",
      reject: "Rejeter",
      transfer: "Transférer à un autre service",
      transferTo: "Service de destination",
      transferConfirm: "Transférer",
      noteLabel: "Note",
      noteRequired: "Une note est obligatoire pour corriger ou rejeter.",
      backToList: "Retour à la file",
      actionDone: "Action enregistrée (exemple).",
      risks: { LOW: "Faible", MEDIUM: "Moyen", HIGH: "Élevé", CRITICAL: "Critique" },
      statuses: {
        OPEN: "Ouvert",
        IN_REVIEW: "En cours",
        APPROVED: "Approuvé",
        CORRECTED: "Corrigé",
        REJECTED: "Rejeté",
        TRANSFERRED: "Transféré",
      },
    },
    admin: {
      overviewTitle: "Vue d'ensemble",
      kpiUsers: "Utilisateurs",
      kpiRequests: "Requêtes aujourd'hui",
      kpiBlocked: "Requêtes bloquées",
      kpiErrors: "Erreurs de workflow",
      chartRequests: "Requêtes par jour (7 jours)",
      chartBlocked: "Requêtes bloquées par type d'attaque",
      usersTitle: "Utilisateurs et rôles",
      colEmail: "E-mail",
      colName: "Nom",
      colRoles: "Rôle",
      colState: "État",
      colActions: "Actions",
      active: "Actif",
      userDisabled: "Désactivé",
      userDisable: "Désactiver",
      userEnable: "Réactiver",
      changeRole: "Modifier",
      save: "Enregistrer",
      cancel: "Annuler",
      auditNote: "Chaque modification est écrite dans le journal d'audit.",
      auditRecent: "Entrées d'audit récentes",
      documentsTitle: "Gestion des documents",
      dropzone: "Glissez-déposez des fichiers ici ou cliquez pour parcourir",
      allowedTypes: "PDF, DOCX, TXT",
      sizeLimit: "Taille maximale : 20 Mo",
      invalidType: "Type de fichier non autorisé.",
      tooLarge: "Fichier trop volumineux.",
      uploadNote:
        "L'ajout d'un document ne le publie jamais — il reste « Importé » jusqu'à validation.",
      colTitle: "Titre",
      colFile: "Fichier",
      colSize: "Taille",
      colStatus: "Statut",
      colDocActions: "Actions",
      docStatuses: {
        UPLOADED: "Importé",
        PARSED: "Analysé",
        PENDING_REVIEW: "En attente de validation",
        APPROVED: "Approuvé",
        DISABLED: "Désactivé",
      },
      sendIndexing: "Envoyer à l'indexation",
      sendReview: "Envoyer à la validation",
      approve: "Approuver",
      reject: "Rejeter",
      disable: "Désactiver",
      retry: "Réessayer",
      previewTitle: "Aperçu du texte extrait",
      previewEmpty: "Sélectionnez un document pour afficher l'aperçu.",
      permissionsTitle: "Permissions des agents",
      colAgent: "Agent",
      colTool: "Outil",
      colOperation: "Opération",
      colAllowed: "Autorisé",
      allow: "Autorisé",
      deny: "Refusé",
      permissionsNote:
        "Matrice stockée dans la table agent_permissions (branchement API à la phase 4).",
      workflowsTitle: "Monitor workflows",
      colWorkflow: "Workflow",
      colStarted: "Démarré",
      colDuration: "Durée",
      colWfStatus: "Statut",
      wfStatuses: { SUCCESS: "Succès", ERROR: "Erreur", RUNNING: "En cours" },
    },
    security: {
      title: "Sécurité et audit",
      incidentsTitle: "Incidents",
      colTime: "Horodatage",
      colAttack: "Type d'attaque",
      colRisk: "Risque",
      colDecision: "Décision",
      colReason: "Motif",
      colContent: "Contenu",
      contentHidden: "Contenu de conversation masqué",
      reveal: "Afficher",
      reasonLabel: "Motif d'accès (obligatoire)",
      reasonPlaceholder: "Ex. : enquête INC-102",
      confirmReveal: "Confirmer l'accès",
      cancel: "Annuler",
      revealNote:
        "Toute consultation du contenu d'une conversation est journalisée avec son motif.",
      blockedTitle: "Requêtes bloquées",
      colRoute: "Point d'entrée",
      redTeamTitle: "Rapports red team",
      colScenario: "Scénario",
      colResult: "Résultat",
      resultBlocked: "Bloqué",
      resultPartial: "Partiel",
      resultFailed: "Échec",
      redTeamDetailsHidden: "Détails réservés à l'auditeur sécurité.",
      details: "Détails",
      auditTitle: "Journal d'audit",
      colActor: "Acteur",
      colAction: "Action",
      colEntity: "Entité",
      attacks: {
        PROMPT_INJECTION: "Injection de prompt",
        ROLE_ESCALATION: "Élévation de rôle",
        DATA_EXFILTRATION: "Exfiltration de données",
        MALICIOUS_FILE: "Fichier malveillant",
        RATE_ABUSE: "Abus de débit",
      },
    },
  },
};

const ar: Dictionary = {
  meta: {
    title: "الدليل الإداري",
    description:
      "مساعد للإجراءات الإدارية في المغرب: الإجراءات الرسمية والوثائق المطلوبة والمصادر القانونية، بالفرنسية والعربية.",
  },
  brand: "الدليل الإداري",
  header: {
    nav: {
      howItWorks: "كيف يعمل",
      services: "الخدمات",
      sources: "المصادر",
      faq: "الأسئلة الشائعة",
    },
    login: "تسجيل الدخول",
    createAccount: "إنشاء حساب",
    menuOpen: "فتح القائمة",
    menuClose: "إغلاق القائمة",
  },
  hero: {
    headline: "إجراءاتك الإدارية، مشروحة ببساطة",
    subtitle:
      "اطرح سؤالك واحصل على الإجراء الرسمي والوثائق المطلوبة والمصادر القانونية — بالفرنسية أو العربية.",
    searchPlaceholder: "مثال: كيف أجدد بطاقة التعريف الوطنية؟",
    search: "بحث",
    examplesLabel: "جرّب:",
    exampleChips: [
      "تجديد جواز السفر",
      "تسجيل مولود في الحالة المدنية",
      "الحصول على شهادة الإقامة",
    ],
    chat: {
      title: "اطرح سؤالك — بدون حساب",
      placeholder: "مثال: كيف أحصل على شهادة التوريث؟",
      button: "اسأل",
      examplesLabel: "جرّب:",
      chips: [
        "كيف أحصل على شهادة التوريث؟",
        "من يتوجب عليه التصريح بالوفاة وفي أي أجل؟",
        "كيف أسجل شركة في السجل التجاري؟",
      ],
      disclaimer:
        "تُولَّد الإجابات حصرياً من الوثائق الرسمية المعتمدة في المنصة، مع مراجعها (الوثيقة، المادة، النسخة). لا تُطلب أي بيانات شخصية.",
      unavailable:
        "خدمة الإجابة غير متوفرة حالياً. أعد المحاولة بعد قليل.",
    },
  },
  howItWorks: {
    title: "كيف يعمل",
    items: [
      {
        title: "اطرح سؤالك",
        description: "صف حالتك بالفرنسية أو العربية بكلماتك الخاصة.",
      },
      {
        title: "احصل على الإجراء",
        description:
          "احصل على الخطوات والوثائق المطلوبة والإدارة المختصة.",
      },
      {
        title: "تحقق من المصادر",
        description:
          "كل إجابة تستشهد بالوثائق الرسمية المعتمدة ونسختها السارية.",
      },
    ],
  },
  services: {
    title: "الخدمات",
    items: [
      {
        title: "الإجراءات",
        description: "الخطوات الرسمية لمعاملاتك، مشروحة خطوة بخطوة.",
      },
      {
        title: "الوثائق المطلوبة",
        description: "قائمة الوثائق الواجب تقديمها لكل ملف.",
      },
      {
        title: "الإدارة المختصة",
        description: "الشباك والجهة المناسبة للتواصل معها.",
      },
      {
        title: "المراجع القانونية",
        description: "النصوص والمواد المُستشهد بها، بنسختها السارية.",
      },
      {
        title: "الإجراءات المحفوظة",
        description: "احفظ معاملاتك للرجوع إليها لاحقًا.",
      },
      {
        title: "طلب مراجعة بشرية",
        description: "يراجع أحد الموظفين الحالات الحساسة قبل الإجابة النهائية.",
      },
    ],
  },
  sources: {
    title: "مصادر رسمية وموثوقة",
    points: [
      {
        title: "وثائق معتمدة فقط",
        description:
          "تستند الإجابات حصريًا إلى وثائق رسمية تم التحقق منها على المنصة.",
      },
      {
        title: "نصوص موثقة بالنسخ",
        description:
          "كل قانون مؤرّخ ومُرقّم بالنسخ؛ تُستخدم النسخة السارية فقط.",
      },
      {
        title: "مراجعة بشرية",
        description: "تُحوّل الحالات الحساسة إلى موظف قبل أي إجابة نهائية.",
      },
    ],
  },
  faq: {
    title: "الأسئلة الشائعة",
    items: [
      {
        question: "من أين تأتي إجابات المساعد؟",
        answer:
          "تُبنى الإجابات حصريًا من وثائق رسمية معتمدة وموثقة بالنسخ على المنصة. لا تُختلق أي إجابة.",
      },
      {
        question: "هل المعلومات المقدمة ملزمة قانونيًا؟",
        answer:
          "الإجابات ذات قيمة استرشادية. لأي تصرف رسمي، ارجع دائمًا إلى النص الساري أو الإدارة المختصة.",
      },
      {
        question: "هل يمكنني استخدام المنصة بالعربية؟",
        answer:
          "نعم. الواجهة والإجابات متوفرة بالفرنسية والعربية، مع عرض مناسب للقراءة من اليمين إلى اليسار.",
      },
      {
        question: "ماذا يحدث إذا كان سؤالي حساسًا؟",
        answer:
          "تُحوّل الحالات الحساسة إلى موظف لمراجعتها بشريًا قبل تقديم إجابة نهائية.",
      },
      {
        question: "كيف تُحمى بياناتي؟",
        answer:
          "تُخزَّن محادثاتك بشكل آمن ويقتصر الوصول على الأدوار المخوّلة، مع تسجيل كل عملية وصول.",
      },
      {
        question: "هل إنشاء الحساب إلزامي؟",
        answer:
          "يمكنك تصفح الصفحات العامة دون حساب. تسجيل الدخول مطلوب لطرح الأسئلة وحفظ الإجراءات.",
      },
    ],
  },
  footer: {
    platformTitle: "المنصة",
    platformLinks: [
      { label: "كيف يعمل", href: "#how-it-works" },
      { label: "الخدمات", href: "#services" },
      { label: "المصادر الرسمية", href: "#sources" },
    ],
    legalTitle: "قانوني",
    legalLinks: [
      { label: "الخصوصية", href: "#" },
      { label: "شروط الاستخدام", href: "#" },
    ],
    contactTitle: "اتصل بنا",
    contactLinks: [
      { label: "مركز المساعدة", href: "#" },
      { label: "الإبلاغ عن مشكلة", href: "#" },
    ],
    languageTitle: "اللغة",
    languageLinks: [
      { label: "Français", href: "/fr", locale: "fr" },
      { label: "العربية", href: "/ar", locale: "ar" },
    ],
    copyright: "© 2026 الدليل الإداري — مشروع توضيحي.",
  },
  auth: {
    login: {
      title: "تسجيل الدخول",
      emailLabel: "البريد الإلكتروني",
      passwordLabel: "كلمة المرور",
      submit: "تسجيل الدخول",
      submitting: "جارٍ تسجيل الدخول…",
      errorInvalid: "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
      errorNotConfirmed: "يرجى تأكيد بريدك الإلكتروني قبل تسجيل الدخول.",
      errorGeneric: "حدث خطأ. يرجى المحاولة مرة أخرى.",
      errorConfig:
        "لم يُضبط تسجيل الدخول: حدّد NEXT_PUBLIC_SUPABASE_URL و NEXT_PUBLIC_SUPABASE_ANON_KEY في frontend/.env.local.",
      noAccount: "ليس لديك حساب؟",
      createAccountLink: "إنشاء حساب",
    },
    register: {
      title: "إنشاء حساب",
      emailLabel: "البريد الإلكتروني",
      passwordLabel: "كلمة المرور",
      confirmPasswordLabel: "تأكيد كلمة المرور",
      submit: "إنشاء حساب",
      submitting: "جارٍ الإنشاء…",
      errorMismatch: "كلمتا المرور غير متطابقتين.",
      errorShort: "يجب أن تتكون كلمة المرور من 8 أحرف على الأقل.",
      errorAlreadyExists: "يوجد حساب بهذا البريد الإلكتروني بالفعل.",
      errorGeneric: "حدث خطأ. يرجى المحاولة مرة أخرى.",
      errorConfig:
        "لم يُضبط تسجيل الدخول: حدّد NEXT_PUBLIC_SUPABASE_URL و NEXT_PUBLIC_SUPABASE_ANON_KEY في frontend/.env.local.",
      haveAccount: "لديك حساب بالفعل؟",
      loginLink: "تسجيل الدخول",
      successMessage:
        "تم إنشاء الحساب. تحقق من بريدك الإلكتروني لتأكيد العنوان إذا كان التأكيد مفعّلًا.",
    },
  },
  common: { backHome: "العودة إلى الرئيسية" },
  dashboard: {
    sidebar: {
      groups: {
        main: "الرئيسي",
        citizen: "فضاء المواطن",
        review: "المراجعة البشرية",
        content: "المحتوى",
        administration: "الإدارة",
        security: "الأمن",
      },
      items: {
        dashboard: "لوحة التحكم",
        chat: "المساعد",
        conversations: "سجل المحادثات",
        saved: "الإجراءات المحفوظة",
        processes: "مساطري",
        reviewQueue: "قائمة المراجعة",
        documents: "إدارة الوثائق",
        overview: "نظرة عامة",
        usersRoles: "المستخدمون والأدوار",
        permissions: "الصلاحيات",
        workflows: "مراقبة سير العمل",
        security: "الأمن والتدقيق",
      },
      disabledHint: "متاح في المرحلة التالية",
    },
    topbar: {
      notifications: "الإشعارات",
      notificationsEmpty: "لا توجد إشعارات.",
      userMenu: "قائمة المستخدم",
      signOut: "تسجيل الخروج",
      menuOpen: "فتح التنقل",
      menuClose: "إغلاق التنقل",
    },
    home: {
      welcome: "مرحبًا",
      rolesLabel: "أدوارك",
      phaseNote:
        "تعتمد أقسام لوحة التحكم الآن على بيانات المنصة الحقيقية (الحساب، المحادثات، مساطرك المحفوظة والخطوات).",
    },
    accessDenied: {
      title: "وصول مقيّد",
      message:
        "حسابك لا يملك الدور اللازم للوصول إلى هذا الفضاء. تواصل مع المسؤول إذا كنت تعتقد أن هذا خطأ.",
      backHome: "العودة إلى الرئيسية",
    },
    roles: {
      VISITOR: "زائر",
      CITIZEN: "مواطن",
      EMPLOYEE: "موظف",
      CONTENT_APPROVER: "مصادح المحتوى",
      SYSTEM_ADMIN: "مسؤول النظام",
      SECURITY_AUDITOR: "مدقق أمني",
      PLATFORM_SUPER_ADMIN: "المسؤول الأعلى",
    },
    citizen: {
      chatTitle: "المساعد",
      chatPlaceholder: "اطرح سؤالك…",
      send: "إرسال",
      engineNote:
        "تأتي الإجابات من محرك المعالجة الرسمي (الوثائق المعتمدة فقط). يتم حفظ المحادثات والمساطر المحفوظة في حسابك.",
      stepsLabel: "الخطوات",
      documentsLabel: "الوثائق المطلوبة",
      administrationLabel: "الإدارة المختصة",
      sourcesLabel: "المصادر",
      saveProcedure: "حفظ الإجراء",
      saved: "محفوظ",
      requestReview: "طلب مراجعة بشرية",
      reviewRequested: "أُحيل إلى المراجعة البشرية",
      suggestedProcedures: "إجراءات مقترحة",
      savedProcedures: "الإجراءات المحفوظة",
      historyTitle: "سجل المحادثات",
      historyEmpty: "لا توجد محادثات حاليًا.",
      savedTitle: "الإجراءات المحفوظة",
      savedEmpty: "لا توجد إجراءات محفوظة حاليًا.",
      messagesLabel: "رسالة",
      updatedLabel: "آخر تحديث",
    },
    employee: {
      queueTitle: "الحالات المطلوب مراجعتها",
      colId: "رقم الحالة",
      colQuestion: "السؤال",
      colRisk: "مستوى الخطورة",
      colStatus: "الحالة",
      colCreated: "تاريخ الإنشاء",
      colService: "الخدمة",
      detailTitle: "تفاصيل الحالة",
      questionLabel: "السؤال",
      proposedAnswerLabel: "الإجابة المقترحة",
      evidenceLabel: "الأدلة القانونية المستخدمة",
      actionsLabel: "الإجراءات",
      approve: "اعتماد",
      correct: "تصحيح",
      reject: "رفض",
      transfer: "التحويل إلى خدمة أخرى",
      transferTo: "الخدمة المقصودة",
      transferConfirm: "تحويل",
      noteLabel: "ملاحظة",
      noteRequired: "الملاحظة إلزامية للتصحيح أو الرفض.",
      backToList: "العودة إلى القائمة",
      actionDone: "تم تسجيل الإجراء (نموذج).",
      risks: { LOW: "منخفض", MEDIUM: "متوسط", HIGH: "مرتفع", CRITICAL: "حرج" },
      statuses: {
        OPEN: "مفتوحة",
        IN_REVIEW: "قيد المراجعة",
        APPROVED: "معتمدة",
        CORRECTED: "مصححة",
        REJECTED: "مرفوضة",
        TRANSFERRED: "محوّلة",
      },
    },
    admin: {
      overviewTitle: "نظرة عامة",
      kpiUsers: "المستخدمون",
      kpiRequests: "طلبات اليوم",
      kpiBlocked: "الطلبات المحظورة",
      kpiErrors: "أخطاء سير العمل",
      chartRequests: "الطلبات اليومية (7 أيام)",
      chartBlocked: "الطلبات المحظورة حسب نوع الهجوم",
      usersTitle: "المستخدمون والأدوار",
      colEmail: "البريد الإلكتروني",
      colName: "الاسم",
      colRoles: "الدور",
      colState: "الحالة",
      colActions: "الإجراءات",
      active: "نشط",
      userDisabled: "معطّل",
      userDisable: "تعطيل",
      userEnable: "إعادة تنشيط",
      changeRole: "تعديل",
      save: "حفظ",
      cancel: "إلغاء",
      auditNote: "كل تعديل يُكتب في سجل التدقيق.",
      auditRecent: "أحدث مدخلات التدقيق",
      documentsTitle: "إدارة الوثائق",
      dropzone: "أفلت الملفات هنا أو انقر للاختيار",
      allowedTypes: "PDF، DOCX، TXT",
      sizeLimit: "الحجم الأقصى: 20 ميغابايت",
      invalidType: "نوع الملف غير مسموح.",
      tooLarge: "الملف كبير جدًا.",
      uploadNote:
        "إضافة وثيقة لا تنشرها أبدًا — تبقى «محمّلة» حتى المصادقة عليها.",
      colTitle: "العنوان",
      colFile: "الملف",
      colSize: "الحجم",
      colStatus: "الحالة",
      colDocActions: "الإجراءات",
      docStatuses: {
        UPLOADED: "محمّلة",
        PARSED: "محلّلة",
        PENDING_REVIEW: "في انتظار المصادقة",
        APPROVED: "معتمدة",
        DISABLED: "معطّلة",
      },
      sendIndexing: "إرسال إلى الفهرسة",
      sendReview: "إرسال إلى المصادقة",
      approve: "اعتماد",
      reject: "رفض",
      disable: "تعطيل",
      retry: "إعادة المحاولة",
      previewTitle: "معاينة النص المستخرج",
      previewEmpty: "اختر وثيقة لعرض المعاينة.",
      permissionsTitle: "صلاحيات الوكلاء",
      colAgent: "الوكيل",
      colTool: "الأداة",
      colOperation: "العملية",
      colAllowed: "مسموح",
      allow: "مسموح",
      deny: "مرفوض",
      permissionsNote:
        "المصفوفة مخزّنة في جدول agent_permissions (يُربَط عبر API في المرحلة 4).",
      workflowsTitle: "مراقبة سير العمل",
      colWorkflow: "سير العمل",
      colStarted: "بدأ في",
      colDuration: "المدة",
      colWfStatus: "الحالة",
      wfStatuses: { SUCCESS: "نجاح", ERROR: "خطأ", RUNNING: "قيد التنفيذ" },
    },
    security: {
      title: "الأمن والتدقيق",
      incidentsTitle: "الحوادث",
      colTime: "التوقيت",
      colAttack: "نوع الهجوم",
      colRisk: "الخطورة",
      colDecision: "القرار",
      colReason: "السبب",
      colContent: "المحتوى",
      contentHidden: "محتوى المحادثة مُخفى",
      reveal: "إظهار",
      reasonLabel: "سبب الوصول (إلزامي)",
      reasonPlaceholder: "مثال: تحقيق INC-102",
      confirmReveal: "تأكيد الوصول",
      cancel: "إلغاء",
      revealNote:
        "كل اطلاع على محتوى محادثة يُسجَّل مع سببه.",
      blockedTitle: "الطلبات المحظورة",
      colRoute: "نقطة الدخول",
      redTeamTitle: "تقارير الفريق الأحمر",
      colScenario: "السيناريو",
      colResult: "النتيجة",
      resultBlocked: "محجوب",
      resultPartial: "جزئي",
      resultFailed: "فاشل",
      redTeamDetailsHidden: "التفاصيل حكر على المدقق الأمني.",
      details: "التفاصيل",
      auditTitle: "سجل التدقيق",
      colActor: "الفاعل",
      colAction: "الإجراء",
      colEntity: "الكيان",
      attacks: {
        PROMPT_INJECTION: "حقن التعليمات",
        ROLE_ESCALATION: "ترقية الصلاحيات",
        DATA_EXFILTRATION: "تسريب البيانات",
        MALICIOUS_FILE: "ملف خبيث",
        RATE_ABUSE: "إساءة الاستخدام",
      },
    },
  },
};

export const dictionaries: Record<Locale, Dictionary> = { fr, ar };

export function getDictionary(locale: Locale): Dictionary {
  return dictionaries[locale];
}
