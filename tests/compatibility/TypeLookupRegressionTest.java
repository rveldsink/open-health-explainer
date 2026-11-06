package org.hl7.fhir.services.elementmodel;

import static org.junit.jupiter.api.Assertions.*;
import java.util.ArrayList;
import java.util.Date;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.hl7.fhir.exceptions.FHIRException;
import org.hl7.fhir.exceptions.FHIRFormatError;
import org.hl7.fhir.model.core.CanonicalResource;
import org.hl7.fhir.model.core.Enumerations.FHIRVersion;
import org.hl7.fhir.model.core.PackageInformation;
import org.hl7.fhir.model.core.StructureDefinition;
import org.hl7.fhir.model.core.StructureDefinition.StructureDefinitionKind;
import org.hl7.fhir.model.core.StructureDefinition.TypeDerivationRule;
import org.hl7.fhir.model.utilities.formats.FormatUtilities;
import org.hl7.fhir.services.context.CanonicalResourceProxy;
import org.hl7.fhir.standalone.context.SimpleWorkerContext;
import org.hl7.fhir.standalone.testing.TestingUtilities;

/** Real parser calls, not a Python imitation of the HL7 resolver. */
class TypeLookupRegressionTest {
  private static class Proxy extends CanonicalResourceProxy {
    private final StructureDefinition definition;
    final AtomicInteger loads = new AtomicInteger();
    Proxy(StructureDefinition sd, String indexedDerivation) {
      super("StructureDefinition", sd.getId(), sd.getUrl(), sd.getVersion(), null,
            indexedDerivation, null);
      definition = sd;
    }
    @Override public CanonicalResource loadResource() throws FHIRException {
      loads.incrementAndGet();
      return definition;
    }
  }

  @ParameterizedTest
  @ValueSource(strings = {"specialization", "constraint"})
  @NullSource
  void resolvesOnlySpecializationsAllowedByIndex(String indexedDerivation) throws Exception {
    SimpleWorkerContext context = new SimpleWorkerContext(
      TestingUtilities.getSharedWorkerContext("5.0.0"));
    StructureDefinition sd = new StructureDefinition();
    sd.setId("ohe-lookup");
    sd.setUrl("https://ohe.test/StructureDefinition/OheLookup");
    sd.setVersion("1.0.0");
    sd.setName("OheLookup");
    sd.setKind(StructureDefinitionKind.RESOURCE);
    sd.setType("OheLookup");
    sd.setDerivation(TypeDerivationRule.SPECIALIZATION);
    sd.setFhirVersion(FHIRVersion._5_0_0);
    sd.getSnapshot().addElement().setPath("OheLookup");
    Proxy proxy = new Proxy(sd, indexedDerivation);
    context.registerResourceFromPackage(proxy,
      new PackageInformation("ohe.lookup", "1.0.0", "5.0.0", new Date()));
    JsonParser parser = new JsonParser(context);
    if ("constraint".equals(indexedDerivation)) {
      assertThrows(FHIRFormatError.class,
        () -> parser.getDefinition(new ArrayList<>(), 0, 0, "OheLookup"));
      assertThrows(FHIRFormatError.class,
        () -> parser.getDefinition(new ArrayList<>(), 0, 0, sd.getUrl()));
      assertThrows(FHIRFormatError.class,
        () -> parser.getDefinition(new ArrayList<>(), 0, 0, FormatUtilities.FHIR_NS, "OheLookup"));
      assertEquals(0, proxy.loads.get(), "misindexed specialization is skipped, not parsed");
    } else {
      assertSame(sd, parser.getDefinition(new ArrayList<>(), 0, 0, "OheLookup"));
      assertSame(sd, parser.getDefinition(new ArrayList<>(), 0, 0, sd.getUrl()));
      assertSame(sd, parser.getDefinition(new ArrayList<>(), 0, 0, FormatUtilities.FHIR_NS, "OheLookup"));
      assertTrue(proxy.loads.get() > 0);
    }
  }
}
